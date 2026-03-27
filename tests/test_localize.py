"""Tests for the core localization tool (download, skip, compose, dedup).

See also:
- test_localize_oci.py  -- OCI-specific skip, integration, and parallel tests
- test_localize_auth.py -- HTTP authentication (netrc, Basic, Bearer, redirect)
"""

import io
import os
from unittest.mock import MagicMock, patch

import pytest

from productmd.images import Image, Images
from productmd.localize import (
    HttpTask,
    LocalizeResult,
    _collect_download_tasks,
    _deduplicate_http_tasks,
    _discover_repodata_tasks,
    _download_https,
    _parse_repomd_xml,
    _should_skip,
    localize_compose,
)
from productmd.location import FileEntry, Location
from productmd.rpms import Rpms
from productmd.version import VERSION_1_2, VERSION_2_0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_image(parent, path, size, checksum_hex):
    img = Image(parent)
    img.path = path
    img.mtime = 1738627200
    img.size = size
    img.volume_id = "Test-1.0"
    img.type = "dvd"
    img.format = "iso"
    img.arch = "x86_64"
    img.disc_number = 1
    img.disc_count = 1
    img.checksums = {"sha256": checksum_hex}
    img.subvariant = "Server"
    return img


def _create_images_v2():
    """Create Images with explicit remote Location objects."""
    im = Images()
    im.header.version = "2.0"
    im.compose.id = "Test-1.0-20260204.0"
    im.compose.type = "production"
    im.compose.date = "20260204"
    im.compose.respin = 0
    im.output_version = VERSION_2_0

    img = _make_image(im, "Server/x86_64/iso/boot.iso", 512, "a" * 64)
    img.location = Location(
        url="https://cdn.example.com/Server/x86_64/iso/boot.iso",
        size=512,
        checksum="sha256:" + "a" * 64,
        local_path="Server/x86_64/iso/boot.iso",
    )
    im.add("Server", "x86_64", img)

    return im


def _create_rpms_v2():
    """Create Rpms with explicit remote Location objects."""
    rpms = Rpms()
    rpms.header.version = "2.0"
    rpms.compose.id = "Test-1.0-20260204.0"
    rpms.compose.type = "production"
    rpms.compose.date = "20260204"
    rpms.compose.respin = 0
    rpms.output_version = VERSION_2_0

    loc = Location(
        url="https://cdn.example.com/Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
        size=1849356,
        checksum="sha256:" + "b" * 64,
        local_path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
    )
    rpms.add(
        variant="Server",
        arch="x86_64",
        nevra="bash-0:5.2.26-3.fc41.x86_64",
        path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
        sigkey="a15b79cc",
        srpm_nevra="bash-0:5.2.26-3.fc41.src",
        category="binary",
        location=loc,
    )
    return rpms


def _create_images_v1():
    """Create Images without Location objects (v1.x data)."""
    im = Images()
    im.header.version = "1.2"
    im.compose.id = "Test-1.0-20260204.0"
    im.compose.type = "production"
    im.compose.date = "20260204"
    im.compose.respin = 0
    im.output_version = VERSION_1_2

    img = _make_image(im, "Server/x86_64/iso/boot.iso", 512, "a" * 64)
    im.add("Server", "x86_64", img)
    return im


def _mock_response(content=b"fake file content", status=200, content_length=None):
    """Create a mock HTTP response for _opener.open()."""
    response = MagicMock()
    data = io.BytesIO(content)
    response.read = data.read
    if content_length is None:
        content_length = str(len(content))
    response.headers = {"Content-Length": content_length}
    response.status = status
    return response


# ---------------------------------------------------------------------------
# Tests: _download_https
# ---------------------------------------------------------------------------


class TestDownloadHttps:
    """Tests for the _download_https function."""

    @patch("productmd.localize._opener.open")
    def test_download_creates_file(self, mock_open, tmp_path):
        """Test that download creates the file at the correct path."""
        mock_open.return_value = _mock_response(b"hello world")
        dest = str(tmp_path / "output" / "test.txt")

        _download_https("https://example.com/test.txt", dest, retries=0)

        assert os.path.isfile(dest)
        with open(dest, "rb") as f:
            assert f.read() == b"hello world"

    @patch("productmd.localize._opener.open")
    def test_download_creates_parent_dirs(self, mock_open, tmp_path):
        """Test that parent directories are created automatically."""
        mock_open.return_value = _mock_response(b"data")
        dest = str(tmp_path / "a" / "b" / "c" / "file.rpm")

        _download_https("https://example.com/file.rpm", dest, retries=0)

        assert os.path.isfile(dest)

    @patch("productmd.localize._opener.open")
    def test_download_atomic_rename(self, mock_open, tmp_path):
        """Test that .tmp file is renamed to final name (no partial files)."""
        mock_open.return_value = _mock_response(b"content")
        dest = str(tmp_path / "final.iso")

        _download_https("https://example.com/final.iso", dest, retries=0)

        assert os.path.isfile(dest)
        assert not os.path.exists(dest + ".tmp")

    @patch("productmd.localize._opener.open")
    @patch("productmd.localize.time.sleep")
    def test_download_retry_on_failure(self, mock_sleep, mock_open, tmp_path):
        """Test that download retries on failure with exponential backoff."""
        from urllib.error import URLError

        mock_open.side_effect = [
            URLError("connection refused"),
            URLError("timeout"),
            _mock_response(b"success"),
        ]
        dest = str(tmp_path / "retried.txt")

        _download_https("https://example.com/retried.txt", dest, retries=2)

        assert os.path.isfile(dest)
        with open(dest, "rb") as f:
            assert f.read() == b"success"
        assert mock_sleep.call_count == 2

    @patch("productmd.localize._opener.open")
    def test_download_calls_progress_callback(self, mock_open, tmp_path):
        """Test that progress callback receives correct events."""
        content = b"x" * 100
        mock_open.return_value = _mock_response(content)
        dest = str(tmp_path / "progress.bin")

        events = []
        _download_https(
            "https://example.com/progress.bin",
            dest,
            retries=0,
            progress_callback=events.append,
            filename="progress.bin",
        )

        event_types = [e.event_type for e in events]
        assert event_types[0] == "start"
        assert event_types[-1] == "complete"
        assert "progress" in event_types

        # Start event has total_bytes from Content-Length
        start = events[0]
        assert start.total_bytes == 100
        assert start.bytes_downloaded == 0

        # Complete event has full size
        complete = events[-1]
        assert complete.bytes_downloaded == 100

    @patch("productmd.localize._opener.open")
    def test_download_all_retries_exhausted(self, mock_open, tmp_path):
        """Test that exception is raised when all retries are exhausted."""
        from urllib.error import URLError

        mock_open.side_effect = URLError("permanent failure")
        dest = str(tmp_path / "fail.txt")

        with pytest.raises(URLError):
            _download_https("https://example.com/fail.txt", dest, retries=1)

    @patch("productmd.localize._opener.open")
    def test_download_no_retry_on_401(self, mock_open, tmp_path):
        """Test that 401 errors are raised immediately without retrying."""
        from urllib.error import HTTPError

        mock_open.side_effect = HTTPError("https://example.com/file.rpm", 401, "Unauthorized", {}, None)
        dest = str(tmp_path / "auth_fail.txt")

        with pytest.raises(HTTPError) as exc_info:
            _download_https("https://example.com/file.rpm", dest, retries=3)

        assert exc_info.value.code == 401
        mock_open.assert_called_once()

    @patch("productmd.localize._opener.open")
    def test_download_no_retry_on_403(self, mock_open, tmp_path):
        """Test that 403 errors are raised immediately without retrying."""
        from urllib.error import HTTPError

        mock_open.side_effect = HTTPError("https://example.com/file.rpm", 403, "Forbidden", {}, None)
        dest = str(tmp_path / "forbidden.txt")

        with pytest.raises(HTTPError) as exc_info:
            _download_https("https://example.com/file.rpm", dest, retries=3)

        assert exc_info.value.code == 403
        mock_open.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: _should_skip
# ---------------------------------------------------------------------------


class TestShouldSkip:
    """Tests for the _should_skip function."""

    def test_file_does_not_exist(self, tmp_path):
        """Test that non-existent files are not skipped."""
        assert not _should_skip(str(tmp_path / "nope"), None, True)

    def test_file_exists_no_verify(self, tmp_path):
        """Test that existing files are skipped when verify_checksums=False."""
        f = tmp_path / "exists.txt"
        f.write_text("content")
        assert _should_skip(str(f), None, False)

    def test_file_exists_with_valid_checksum(self, tmp_path):
        """Test that files with matching checksum are skipped."""
        f = tmp_path / "valid.txt"
        f.write_bytes(b"test content")

        from productmd.location import compute_checksum as cc

        checksum = cc(str(f), "sha256")
        size = os.path.getsize(str(f))

        loc = Location(url="https://x", size=size, checksum=checksum, local_path="valid.txt")
        assert _should_skip(str(f), loc, True)

    def test_file_exists_with_wrong_checksum(self, tmp_path):
        """Test that files with wrong checksum are not skipped."""
        f = tmp_path / "wrong.txt"
        f.write_bytes(b"test content")

        loc = Location(url="https://x", size=12, checksum="sha256:" + "f" * 64, local_path="wrong.txt")
        assert not _should_skip(str(f), loc, True)

    def test_file_exists_no_checksum_available(self, tmp_path):
        """Test that files without checksum fall back to existence check."""
        f = tmp_path / "no_checksum.txt"
        f.write_text("content")

        loc = Location(url="https://x", local_path="no_checksum.txt")
        assert _should_skip(str(f), loc, True)


# ---------------------------------------------------------------------------
# Tests: localize_compose
# ---------------------------------------------------------------------------


class TestLocalizeCompose:
    """Tests for the localize_compose function."""

    @patch("productmd.localize._opener.open")
    def test_basic_localize(self, mock_open, tmp_path):
        """Test basic localization downloads files and writes v1.2 metadata."""
        mock_open.return_value = _mock_response(b"iso content")
        output_dir = str(tmp_path / "compose-output")

        im = _create_images_v2()
        result = localize_compose(
            output_dir=output_dir,
            images=im,
            parallel_downloads=1,
            verify_checksums=False,
            retries=0,
        )

        assert result.downloaded == 1
        assert result.failed == 0

        # Verify file was downloaded
        expected = os.path.join(output_dir, "compose", "Server", "x86_64", "iso", "boot.iso")
        assert os.path.isfile(expected)

        # Verify v1.2 metadata was written
        metadata_dir = os.path.join(output_dir, "compose", "metadata")
        assert os.path.isfile(os.path.join(metadata_dir, "images.json"))

    @patch("productmd.localize._opener.open")
    def test_skip_existing_with_valid_checksum(self, mock_open, tmp_path):
        """Test that existing files with valid checksum are skipped."""
        output_dir = str(tmp_path / "compose-output")

        # Pre-create the file
        file_path = os.path.join(output_dir, "compose", "Server", "x86_64", "iso", "boot.iso")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(b"existing content")

        im = _create_images_v2()
        # Update location checksum to match the pre-created file
        from productmd.location import compute_checksum as cc

        checksum = cc(file_path, "sha256")
        size = os.path.getsize(file_path)
        for image in im.images["Server"]["x86_64"]:
            image.location = Location(
                url="https://cdn.example.com/Server/x86_64/iso/boot.iso",
                size=size,
                checksum=checksum,
                local_path="Server/x86_64/iso/boot.iso",
            )

        result = localize_compose(
            output_dir=output_dir,
            images=im,
            skip_existing=True,
            verify_checksums=True,
            retries=0,
        )

        assert result.skipped == 1
        assert result.downloaded == 0
        # urlopen should not have been called
        mock_open.assert_not_called()

    @patch("productmd.localize._opener.open")
    @patch("productmd.localize._should_skip")
    def test_skip_existing_wrong_checksum_redownloads(self, mock_skip, mock_open, tmp_path):
        """Test that files with wrong checksum are re-downloaded when skip returns False."""
        mock_skip.return_value = False  # Simulate checksum mismatch
        mock_open.return_value = _mock_response(b"correct content")

        im = _create_images_v2()
        result = localize_compose(
            output_dir=str(tmp_path / "output"),
            images=im,
            skip_existing=True,
            verify_checksums=False,  # Don't verify after download
            parallel_downloads=1,
            retries=0,
        )

        assert result.downloaded == 1
        assert result.skipped == 0
        mock_skip.assert_called_once()

    @patch("productmd.oci.get_downloader")
    @patch("productmd.oci.HAS_ORAS", True)
    def test_oci_simple_download(self, mock_get_downloader, tmp_path):
        """Test that simple OCI URLs (no contents) are downloaded via oras."""
        mock_downloader = MagicMock()
        mock_get_downloader.return_value = mock_downloader

        im = Images()
        im.header.version = "2.0"
        im.compose.id = "Test-1.0-20260204.0"
        im.compose.type = "production"
        im.compose.date = "20260204"
        im.compose.respin = 0
        im.output_version = VERSION_2_0

        oci_url = "oci://quay.io/fedora/server:41-x86_64@sha256:" + "a" * 64
        img = _make_image(im, "Server/x86_64/iso/boot.iso", 512, "a" * 64)
        img.location = Location(
            url=oci_url,
            size=512,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/iso/boot.iso",
        )
        im.add("Server", "x86_64", img)

        result = localize_compose(
            output_dir=str(tmp_path / "output"),
            images=im,
            verify_checksums=False,
        )

        assert result.downloaded == 1
        assert result.failed == 0
        mock_downloader.download_and_extract.assert_called_once()
        call_kwargs = mock_downloader.download_and_extract.call_args[1]
        assert call_kwargs["oci_url"] == oci_url
        assert call_kwargs["contents"] is None

    @patch("productmd.oci.get_downloader")
    @patch("productmd.oci.HAS_ORAS", True)
    def test_oci_with_contents_download(self, mock_get_downloader, tmp_path):
        """Test that OCI URLs with contents pass FileEntry list to downloader."""
        mock_downloader = MagicMock()
        mock_get_downloader.return_value = mock_downloader

        im = Images()
        im.header.version = "2.0"
        im.compose.id = "Test-1.0-20260204.0"
        im.compose.type = "production"
        im.compose.date = "20260204"
        im.compose.respin = 0
        im.output_version = VERSION_2_0

        contents = [
            FileEntry(file="pxeboot/vmlinuz", size=100, checksum="sha256:" + "d" * 64, layer_digest="sha256:" + "d" * 64),
            FileEntry(file="pxeboot/initrd.img", size=200, checksum="sha256:" + "e" * 64, layer_digest="sha256:" + "e" * 64),
        ]
        oci_url = "oci://quay.io/fedora/boot:41-x86_64@sha256:" + "a" * 64
        img = _make_image(im, "Server/x86_64/os/images/pxeboot/vmlinuz", 100, "d" * 64)
        img.location = Location(
            url=oci_url,
            size=300,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/images",
            contents=contents,
        )
        im.add("Server", "x86_64", img)

        result = localize_compose(
            output_dir=str(tmp_path / "output"),
            images=im,
            verify_checksums=False,
        )

        # 2 files in contents
        assert result.downloaded == 2
        assert result.failed == 0
        mock_downloader.download_and_extract.assert_called_once()
        call_kwargs = mock_downloader.download_and_extract.call_args[1]
        assert call_kwargs["contents"] == contents

    @patch("productmd.oci.HAS_ORAS", False)
    def test_oci_url_without_oras_raises_runtime_error(self, tmp_path):
        """Test that OCI URLs without oras-py installed raise RuntimeError."""
        im = Images()
        im.header.version = "2.0"
        im.compose.id = "Test-1.0-20260204.0"
        im.compose.type = "production"
        im.compose.date = "20260204"
        im.compose.respin = 0
        im.output_version = VERSION_2_0

        img = _make_image(im, "Server/x86_64/iso/boot.iso", 512, "a" * 64)
        img.location = Location(
            url="oci://quay.io/fedora/server:41-x86_64@sha256:" + "a" * 64,
            size=512,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/iso/boot.iso",
        )
        im.add("Server", "x86_64", img)

        with pytest.raises(RuntimeError, match="oras-py is required"):
            localize_compose(
                output_dir=str(tmp_path / "output"),
                images=im,
            )

    @patch("productmd.localize._opener.open")
    def test_fail_fast_stops_on_error(self, mock_open, tmp_path):
        """Test that fail_fast=True stops on first download failure."""
        from urllib.error import URLError

        mock_open.side_effect = URLError("connection refused")

        im = _create_images_v2()
        rpms = _create_rpms_v2()

        result = localize_compose(
            output_dir=str(tmp_path / "output"),
            images=im,
            rpms=rpms,
            fail_fast=True,
            parallel_downloads=1,
            retries=0,
        )

        assert result.failed >= 1
        # Should not have attempted all downloads
        assert result.downloaded == 0

    @patch("productmd.localize._opener.open")
    def test_fail_fast_false_continues(self, mock_open, tmp_path):
        """Test that fail_fast=False continues after errors."""
        from urllib.error import URLError

        # First call fails, second succeeds
        mock_open.side_effect = [
            URLError("connection refused"),
            _mock_response(b"rpm content"),
        ]

        im = _create_images_v2()
        rpms = _create_rpms_v2()

        result = localize_compose(
            output_dir=str(tmp_path / "output"),
            images=im,
            rpms=rpms,
            fail_fast=False,
            verify_checksums=False,
            parallel_downloads=1,
            retries=0,
        )

        assert result.failed == 1
        assert result.downloaded == 1
        assert len(result.errors) == 1

    def test_skip_non_remote_locations(self, tmp_path):
        """Test that v1.x data with no remote URLs produces no downloads."""
        im = _create_images_v1()

        result = localize_compose(
            output_dir=str(tmp_path / "output"),
            images=im,
            parallel_downloads=1,
        )

        assert result.downloaded == 0
        assert result.skipped == 0
        assert result.failed == 0

    @patch("productmd.localize._opener.open")
    def test_localize_result_counts(self, mock_open, tmp_path):
        """Test that LocalizeResult has correct counts."""
        mock_open.return_value = _mock_response(b"data")

        im = _create_images_v2()
        result = localize_compose(
            output_dir=str(tmp_path / "output"),
            images=im,
            parallel_downloads=1,
            verify_checksums=False,
            retries=0,
        )

        assert isinstance(result, LocalizeResult)
        assert result.downloaded == 1
        assert result.skipped == 0
        assert result.failed == 0
        assert result.errors == []

    @patch("productmd.localize._opener.open")
    def test_progress_callback_receives_events(self, mock_open, tmp_path):
        """Test that progress callback receives download events."""
        mock_open.return_value = _mock_response(b"file data")

        im = _create_images_v2()
        events = []

        localize_compose(
            output_dir=str(tmp_path / "output"),
            images=im,
            parallel_downloads=1,
            verify_checksums=False,
            retries=0,
            progress_callback=events.append,
        )

        event_types = [e.event_type for e in events]
        assert "start" in event_types
        assert "complete" in event_types

    @patch("productmd.localize._opener.open")
    def test_metadata_downgraded_to_v12(self, mock_open, tmp_path):
        """Test that output metadata is written in v1.2 format."""
        import json

        mock_open.return_value = _mock_response(b"content")

        im = _create_images_v2()
        output_dir = str(tmp_path / "output")

        localize_compose(
            output_dir=output_dir,
            images=im,
            parallel_downloads=1,
            verify_checksums=False,
            retries=0,
        )

        metadata_file = os.path.join(output_dir, "compose", "metadata", "images.json")
        with open(metadata_file) as f:
            data = json.load(f)

        assert data["header"]["version"] == "1.2"
        # v1.2 format should have "path", not "location"
        img = data["payload"]["images"]["Server"]["x86_64"][0]
        assert "path" in img
        assert "location" not in img


# ---------------------------------------------------------------------------
# Tests: HTTP task deduplication
# ---------------------------------------------------------------------------


class TestDeduplicateHttpTasks:
    """Tests for _deduplicate_http_tasks conflict detection."""

    def test_same_url_same_dest_deduplicates(self):
        """Test that identical tasks are deduplicated silently."""
        task = HttpTask(
            url="https://cdn.example.com/boot.iso",
            dest_path="/tmp/compose/Server/x86_64/iso/boot.iso",
            location=None,
            rel_path="Server/x86_64/iso/boot.iso",
        )
        result = _deduplicate_http_tasks([task, task])
        assert len(result) == 1
        assert result[0] is task

    def test_different_url_same_dest_raises(self):
        """Test that conflicting URLs for the same dest_path raise ValueError."""
        task1 = HttpTask(
            url="https://cdn-a.example.com/boot.iso",
            dest_path="/tmp/compose/Server/x86_64/iso/boot.iso",
            location=None,
            rel_path="Server/x86_64/iso/boot.iso",
        )
        task2 = HttpTask(
            url="https://cdn-b.example.com/boot.iso",
            dest_path="/tmp/compose/Server/x86_64/iso/boot.iso",
            location=None,
            rel_path="Server/x86_64/iso/boot.iso",
        )
        with pytest.raises(ValueError, match="Conflicting URLs"):
            _deduplicate_http_tasks([task1, task2])

    def test_same_url_different_dest_keeps_both(self):
        """Test that same URL targeting different paths keeps both."""
        task1 = HttpTask(
            url="https://cdn.example.com/boot.iso",
            dest_path="/tmp/compose/Server/x86_64/iso/boot.iso",
            location=None,
            rel_path="Server/x86_64/iso/boot.iso",
        )
        task2 = HttpTask(
            url="https://cdn.example.com/boot.iso",
            dest_path="/tmp/compose/Workstation/x86_64/iso/boot.iso",
            location=None,
            rel_path="Workstation/x86_64/iso/boot.iso",
        )
        result = _deduplicate_http_tasks([task1, task2])
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Tests: _parse_repomd_xml
# ---------------------------------------------------------------------------


class TestParseRepomdXml:
    """Tests for repomd.xml parsing."""

    SAMPLE_REPOMD = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<repomd xmlns="http://linux.duke.edu/metadata/repo">
  <revision>1701388800</revision>
  <data type="primary">
    <checksum type="sha256">abc123</checksum>
    <location href="repodata/abc123-primary.xml.gz"/>
    <size>12345</size>
  </data>
  <data type="filelists">
    <checksum type="sha256">def456</checksum>
    <location href="repodata/def456-filelists.xml.gz"/>
    <size>67890</size>
  </data>
  <data type="other">
    <location href="repodata/ghi789-other.xml.gz"/>
  </data>
</repomd>
"""

    def test_parses_all_data_entries(self):
        """Test that all <data> entries with <location> are parsed."""
        entries = _parse_repomd_xml(self.SAMPLE_REPOMD)
        assert len(entries) == 3

    def test_extracts_href(self):
        """Test that href values are extracted correctly."""
        entries = _parse_repomd_xml(self.SAMPLE_REPOMD)
        hrefs = [e["href"] for e in entries]
        assert "repodata/abc123-primary.xml.gz" in hrefs
        assert "repodata/def456-filelists.xml.gz" in hrefs
        assert "repodata/ghi789-other.xml.gz" in hrefs

    def test_extracts_checksum(self):
        """Test that checksum type and value are extracted."""
        entries = _parse_repomd_xml(self.SAMPLE_REPOMD)
        primary = [e for e in entries if "primary" in e["href"]][0]
        assert primary["checksum_type"] == "sha256"
        assert primary["checksum"] == "abc123"

    def test_extracts_size(self):
        """Test that size is extracted as an integer."""
        entries = _parse_repomd_xml(self.SAMPLE_REPOMD)
        primary = [e for e in entries if "primary" in e["href"]][0]
        assert primary["size"] == 12345

    def test_missing_checksum_omitted(self):
        """Test that entries without checksum don't have checksum keys."""
        entries = _parse_repomd_xml(self.SAMPLE_REPOMD)
        other = [e for e in entries if "other" in e["href"]][0]
        assert "checksum" not in other

    def test_missing_size_omitted(self):
        """Test that entries without size don't have size key."""
        entries = _parse_repomd_xml(self.SAMPLE_REPOMD)
        other = [e for e in entries if "other" in e["href"]][0]
        assert "size" not in other

    def test_empty_repomd(self):
        """Test that an empty repomd.xml returns no entries."""
        xml = b'<repomd xmlns="http://linux.duke.edu/metadata/repo"></repomd>'
        entries = _parse_repomd_xml(xml)
        assert entries == []

    def test_data_without_location_skipped(self):
        """Test that <data> elements without <location> are skipped."""
        xml = b"""\
<repomd xmlns="http://linux.duke.edu/metadata/repo">
  <data type="primary">
    <checksum type="sha256">abc123</checksum>
  </data>
</repomd>
"""
        entries = _parse_repomd_xml(xml)
        assert entries == []


# ---------------------------------------------------------------------------
# Tests: _discover_repodata_tasks
# ---------------------------------------------------------------------------


class TestDiscoverRepodataTasks:
    """Tests for repodata task discovery."""

    SAMPLE_REPOMD = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<repomd xmlns="http://linux.duke.edu/metadata/repo">
  <data type="primary">
    <checksum type="sha256">abc123</checksum>
    <location href="repodata/abc123-primary.xml.gz"/>
    <size>12345</size>
  </data>
  <data type="filelists">
    <checksum type="sha256">def456</checksum>
    <location href="repodata/def456-filelists.xml.gz"/>
    <size>67890</size>
  </data>
</repomd>
"""

    @patch("productmd.localize.urllib.request.urlopen")
    def test_generates_tasks_for_repodata_files(self, mock_urlopen, tmp_path):
        """Test that HttpTasks are created for each file in repomd.xml."""
        mock_response = MagicMock()
        mock_response.read.return_value = self.SAMPLE_REPOMD
        mock_urlopen.return_value = mock_response

        compose_root = str(tmp_path / "compose")
        repo_entries = [
            ("https://cdn.example.com/BaseOS/x86_64/os", "BaseOS/x86_64/os"),
        ]

        tasks = _discover_repodata_tasks(repo_entries, compose_root, retries=0)

        assert len(tasks) == 2
        urls = {t.url for t in tasks}
        assert "https://cdn.example.com/BaseOS/x86_64/os/repodata/abc123-primary.xml.gz" in urls
        assert "https://cdn.example.com/BaseOS/x86_64/os/repodata/def456-filelists.xml.gz" in urls

    @patch("productmd.localize.urllib.request.urlopen")
    def test_saves_repomd_xml_locally(self, mock_urlopen, tmp_path):
        """Test that repomd.xml is written to the correct local path."""
        mock_response = MagicMock()
        mock_response.read.return_value = self.SAMPLE_REPOMD
        mock_urlopen.return_value = mock_response

        compose_root = str(tmp_path / "compose")
        repo_entries = [
            ("https://cdn.example.com/BaseOS/x86_64/os", "BaseOS/x86_64/os"),
        ]

        _discover_repodata_tasks(repo_entries, compose_root, retries=0)

        repomd_path = os.path.join(compose_root, "BaseOS/x86_64/os/repodata/repomd.xml")
        assert os.path.isfile(repomd_path)
        with open(repomd_path, "rb") as f:
            assert f.read() == self.SAMPLE_REPOMD

    @patch("productmd.localize.urllib.request.urlopen")
    def test_deduplicates_repos_by_url(self, mock_urlopen, tmp_path):
        """Test that the same repo URL is only fetched once."""
        mock_response = MagicMock()
        mock_response.read.return_value = self.SAMPLE_REPOMD
        mock_urlopen.return_value = mock_response

        compose_root = str(tmp_path / "compose")
        repo_entries = [
            ("https://cdn.example.com/BaseOS/source/tree", "BaseOS/source/tree"),
            ("https://cdn.example.com/BaseOS/source/tree", "BaseOS/source/tree"),
        ]

        tasks = _discover_repodata_tasks(repo_entries, compose_root, retries=0)

        # Only fetched once despite two identical entries
        mock_urlopen.assert_called_once()
        assert len(tasks) == 2

    @patch("productmd.localize.urllib.request.urlopen")
    def test_dest_paths_are_correct(self, mock_urlopen, tmp_path):
        """Test that dest_path values point to the right local paths."""
        mock_response = MagicMock()
        mock_response.read.return_value = self.SAMPLE_REPOMD
        mock_urlopen.return_value = mock_response

        compose_root = str(tmp_path / "compose")
        repo_entries = [
            ("https://cdn.example.com/BaseOS/x86_64/os", "BaseOS/x86_64/os"),
        ]

        tasks = _discover_repodata_tasks(repo_entries, compose_root, retries=0)

        dest_paths = {t.dest_path for t in tasks}
        expected_primary = os.path.join(compose_root, "BaseOS/x86_64/os/repodata/abc123-primary.xml.gz")
        expected_filelists = os.path.join(compose_root, "BaseOS/x86_64/os/repodata/def456-filelists.xml.gz")
        assert expected_primary in dest_paths
        assert expected_filelists in dest_paths

    @patch("productmd.localize.urllib.request.urlopen")
    def test_fetch_failure_skips_repo(self, mock_urlopen, tmp_path):
        """Test that a failed repomd.xml fetch skips the repo gracefully."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("connection refused")

        compose_root = str(tmp_path / "compose")
        repo_entries = [
            ("https://cdn.example.com/BaseOS/x86_64/os", "BaseOS/x86_64/os"),
        ]

        tasks = _discover_repodata_tasks(repo_entries, compose_root, retries=0)

        assert tasks == []

    @patch("productmd.localize.urllib.request.urlopen")
    def test_invalid_xml_skips_repo(self, mock_urlopen, tmp_path):
        """Test that invalid XML in repomd.xml skips the repo gracefully."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"<not valid xml"
        mock_urlopen.return_value = mock_response

        compose_root = str(tmp_path / "compose")
        repo_entries = [
            ("https://cdn.example.com/BaseOS/x86_64/os", "BaseOS/x86_64/os"),
        ]

        tasks = _discover_repodata_tasks(repo_entries, compose_root, retries=0)

        assert tasks == []

    @patch("productmd.localize._opener.open")
    def test_rejects_path_traversal_in_href(self, mock_open, tmp_path):
        """Test that hrefs with .. or absolute paths are rejected."""
        malicious_repomd = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<repomd xmlns="http://linux.duke.edu/metadata/repo">
  <data type="primary">
    <location href="../../etc/passwd"/>
  </data>
  <data type="filelists">
    <location href="/etc/shadow"/>
  </data>
  <data type="other">
    <location href="repodata/legit-other.xml.gz"/>
  </data>
</repomd>
"""
        mock_response = MagicMock()
        mock_response.read.return_value = malicious_repomd
        mock_open.return_value = mock_response

        compose_root = str(tmp_path / "compose")
        repo_entries = [
            ("https://cdn.example.com/BaseOS/x86_64/os", "BaseOS/x86_64/os"),
        ]

        tasks = _discover_repodata_tasks(repo_entries, compose_root, retries=0)

        # Only the legitimate href should produce a task
        assert len(tasks) == 1
        assert "legit-other.xml.gz" in tasks[0].url


# ---------------------------------------------------------------------------
# Tests: _collect_download_tasks with repository variant paths
# ---------------------------------------------------------------------------


class TestCollectRepoEntries:
    """Tests that _collect_download_tasks collects repository entries."""

    def test_collects_repository_entries(self, tmp_path):
        """Test that repository variant paths are collected as repo entries."""
        from productmd.composeinfo import ComposeInfo, Variant

        ci = ComposeInfo()
        ci.release.name = "Fedora"
        ci.release.short = "Fedora"
        ci.release.version = "41"
        ci.release.type = "ga"
        ci.compose.id = "Fedora-41-20260204.0"
        ci.compose.type = "production"
        ci.compose.date = "20260204"
        ci.compose.respin = 0

        variant = Variant(ci)
        variant.id = "Server"
        variant.uid = "Server"
        variant.name = "Fedora Server"
        variant.type = "variant"
        variant.arches = {"x86_64"}
        ci.variants.add(variant)

        # Set repository with a Location (v2.0 style)
        repo_loc = Location(
            url="https://cdn.example.com/Server/x86_64/os",
            local_path="Server/x86_64/os",
        )
        variant.paths.set_location("repository", "x86_64", repo_loc)

        # Set os_tree with a Location (should NOT be collected)
        tree_loc = Location(
            url="https://cdn.example.com/Server/x86_64/os",
            local_path="Server/x86_64/os",
        )
        variant.paths.set_location("os_tree", "x86_64", tree_loc)

        http_tasks, oci_tasks, repo_entries = _collect_download_tasks(str(tmp_path), composeinfo=ci)

        assert len(http_tasks) == 0
        assert len(oci_tasks) == 0
        assert len(repo_entries) == 1
        assert repo_entries[0] == ("https://cdn.example.com/Server/x86_64/os", "Server/x86_64/os")

    def test_collects_all_three_repo_fields(self, tmp_path):
        """Test that repository, debug_repository, and source_repository are all collected."""
        from productmd.composeinfo import ComposeInfo, Variant

        ci = ComposeInfo()
        ci.release.name = "Fedora"
        ci.release.short = "Fedora"
        ci.release.version = "41"
        ci.release.type = "ga"
        ci.compose.id = "Fedora-41-20260204.0"
        ci.compose.type = "production"
        ci.compose.date = "20260204"
        ci.compose.respin = 0

        variant = Variant(ci)
        variant.id = "Server"
        variant.uid = "Server"
        variant.name = "Fedora Server"
        variant.type = "variant"
        variant.arches = {"x86_64"}
        ci.variants.add(variant)

        for field, path in [
            ("repository", "Server/x86_64/os"),
            ("debug_repository", "Server/x86_64/debug/tree"),
            ("source_repository", "Server/source/tree"),
        ]:
            arch = "x86_64" if "source" not in field else "src"
            loc = Location(
                url=f"https://cdn.example.com/{path}",
                local_path=path,
            )
            variant.paths.set_location(field, arch, loc)

        http_tasks, oci_tasks, repo_entries = _collect_download_tasks(str(tmp_path), composeinfo=ci)

        assert len(repo_entries) == 3
        repo_urls = {r[0] for r in repo_entries}
        assert "https://cdn.example.com/Server/x86_64/os" in repo_urls
        assert "https://cdn.example.com/Server/x86_64/debug/tree" in repo_urls
        assert "https://cdn.example.com/Server/source/tree" in repo_urls
