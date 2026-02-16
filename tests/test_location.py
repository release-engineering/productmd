# -*- coding: utf-8 -*-

# Copyright (C) 2024  Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import os
import tempfile

import pytest

from productmd.location import (
    Location,
    FileEntry,
    compute_checksum,
    parse_checksum,
    CHECKSUM_RE,
    OCI_REFERENCE_RE,
)


class TestChecksumUtilities:
    """Tests for checksum utility functions."""

    def test_compute_checksum(self):
        """Test computing checksum of a file."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"hello world\n")
            path = f.name

        try:
            checksum = compute_checksum(path)
            assert checksum.startswith("sha256:")
            assert len(checksum) == 7 + 64  # "sha256:" + 64 hex chars
        finally:
            os.unlink(path)

    def test_compute_checksum_sha512(self):
        """Test computing checksum with different algorithm."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test data")
            path = f.name

        try:
            checksum = compute_checksum(path, "sha512")
            assert checksum.startswith("sha512:")
            assert len(checksum) == 7 + 128  # "sha512:" + 128 hex chars
        finally:
            os.unlink(path)

    @pytest.mark.parametrize(
        "input_str, expected_algo, expected_digest",
        [
            ("sha256:" + "a" * 64, "sha256", "a" * 64),
            ("sha512:" + "b" * 128, "sha512", "b" * 128),
            ("sha1:" + "c" * 40, "sha1", "c" * 40),
            ("md5:" + "d" * 32, "md5", "d" * 32),
        ],
    )
    def test_parse_checksum_valid(self, input_str, expected_algo, expected_digest):
        """Test parsing valid checksum strings."""
        algo, digest = parse_checksum(input_str)
        assert algo == expected_algo
        assert digest == expected_digest

    @pytest.mark.parametrize("invalid", ["invalid", "sha256", "sha999:abcd"])
    def test_parse_checksum_invalid(self, invalid):
        """Test parsing invalid checksum strings."""
        with pytest.raises(ValueError):
            parse_checksum(invalid)

    @pytest.mark.parametrize(
        "value, should_match",
        [
            ("sha256:" + "a" * 64, True),
            ("sha512:" + "b" * 128, True),
            ("sha1:" + "c" * 40, True),
            ("md5:" + "d" * 32, True),
            ("sha999:abcd", False),
            ("invalid", False),
        ],
    )
    def test_checksum_regex(self, value, should_match):
        """Test checksum regex pattern."""
        result = CHECKSUM_RE.match(value)
        if should_match:
            assert result is not None, "expected match for: %s" % value
        else:
            assert result is None, "expected no match for: %s" % value


class TestOCIReferenceRegex:
    """Tests for OCI reference regex pattern."""

    @pytest.mark.parametrize(
        "url, registry, repository, tag",
        [
            (
                "oci://quay.io/fedora/rpms:bash@sha256:" + "a" * 64,
                "quay.io",
                "fedora/rpms",
                "bash",
            ),
            (
                "oci://registry.example.com/namespace/image@sha256:" + "b" * 64,
                "registry.example.com",
                "namespace/image",
                None,
            ),
            (
                "oci://quay.io/org/repo:tag-with-dashes@sha256:" + "c" * 64,
                "quay.io",
                "org/repo",
                "tag-with-dashes",
            ),
        ],
    )
    def test_valid_oci_references(self, url, registry, repository, tag):
        """Test valid OCI reference patterns."""
        match = OCI_REFERENCE_RE.match(url)
        assert match is not None, "expected match for: %s" % url
        assert match.group("registry") == registry
        assert match.group("repository") == repository
        assert match.group("tag") == tag

    @pytest.mark.parametrize(
        "url",
        [
            "oci://quay.io/fedora/rpms:bash",  # missing digest
            "https://quay.io/fedora/rpms@sha256:" + "a" * 64,  # wrong scheme
            "oci://quay.io@sha256:" + "a" * 64,  # missing repository
        ],
    )
    def test_invalid_oci_references(self, url):
        """Test invalid OCI reference patterns."""
        assert OCI_REFERENCE_RE.match(url) is None, "expected no match for: %s" % url


class TestFileEntry:
    """Tests for FileEntry class."""

    def test_create_file_entry(self):
        """Test creating a FileEntry."""
        entry = FileEntry(
            file="pxeboot/vmlinuz",
            size=11534336,
            checksum="sha256:" + "a" * 64,
            layer_digest="sha256:" + "b" * 64,
        )
        assert entry.file == "pxeboot/vmlinuz"
        assert entry.size == 11534336
        entry.validate()

    def test_file_entry_serialize(self):
        """Test FileEntry serialization."""
        entry = FileEntry(
            file="pxeboot/vmlinuz",
            size=11534336,
            checksum="sha256:" + "a" * 64,
            layer_digest="sha256:" + "b" * 64,
        )
        data = entry.serialize()
        assert data["file"] == "pxeboot/vmlinuz"
        assert data["size"] == 11534336
        assert data["checksum"] == "sha256:" + "a" * 64
        assert data["layer_digest"] == "sha256:" + "b" * 64

    def test_file_entry_deserialize(self):
        """Test FileEntry deserialization."""
        data = {
            "file": "pxeboot/initrd.img",
            "size": 89478656,
            "checksum": "sha256:" + "c" * 64,
            "layer_digest": "sha256:" + "d" * 64,
        }
        entry = FileEntry.from_dict(data)
        assert entry.file == "pxeboot/initrd.img"
        assert entry.size == 89478656

    def test_file_entry_equality(self):
        """Test FileEntry equality comparison."""
        entry1 = FileEntry(
            file="test.txt",
            size=100,
            checksum="sha256:" + "a" * 64,
            layer_digest="sha256:" + "b" * 64,
        )
        entry2 = FileEntry(
            file="test.txt",
            size=100,
            checksum="sha256:" + "a" * 64,
            layer_digest="sha256:" + "b" * 64,
        )
        entry3 = FileEntry(
            file="other.txt",
            size=100,
            checksum="sha256:" + "a" * 64,
            layer_digest="sha256:" + "b" * 64,
        )
        assert entry1 == entry2
        assert entry1 != entry3

    @pytest.mark.parametrize(
        "file, size, checksum, layer_digest, desc",
        [
            ("/absolute/path", 100, "sha256:" + "a" * 64, "sha256:" + "b" * 64, "absolute path"),
            ("test.txt", -100, "sha256:" + "a" * 64, "sha256:" + "b" * 64, "negative size"),
            ("test.txt", 100, "invalid", "sha256:" + "b" * 64, "invalid checksum"),
            ("test.txt", 100, "sha256:" + "a" * 64, "invalid", "invalid layer_digest"),
        ],
    )
    def test_file_entry_validation_errors(self, file, size, checksum, layer_digest, desc):
        """Test that invalid FileEntry fields are rejected: %s."""
        entry = FileEntry(file=file, size=size, checksum=checksum, layer_digest=layer_digest)
        with pytest.raises(ValueError):
            entry.validate()


class TestLocation:
    """Tests for Location class."""

    @pytest.mark.parametrize(
        "url, is_https, is_http, is_oci, is_local, is_remote",
        [
            ("https://cdn.example.com/Packages/bash-5.2.rpm", True, False, False, False, True),
            ("http://mirror.example.com/Packages/bash-5.2.rpm", False, True, False, False, True),
            ("oci://quay.io/fedora/rpms:bash@sha256:" + "a" * 64, False, False, True, False, True),
            ("Server/x86_64/os/Packages/b/bash-5.2.rpm", False, False, False, True, False),
        ],
    )
    def test_url_scheme_detection(self, url, is_https, is_http, is_oci, is_local, is_remote):
        """Test URL scheme detection properties."""
        loc = Location(
            url=url,
            size=1849356,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/Packages/b/bash-5.2.rpm",
        )
        assert loc.is_https is is_https
        assert loc.is_http is is_http
        assert loc.is_oci is is_oci
        assert loc.is_local is is_local
        assert loc.is_remote is is_remote
        loc.validate()

    def test_oci_properties(self):
        """Test OCI-specific properties."""
        loc = Location(
            url="oci://quay.io/fedora/boot-files:server-39-x86_64@sha256:" + "a" * 64,
            size=101376000,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/images",
        )
        assert loc.oci_registry == "quay.io"
        assert loc.oci_repository == "fedora/boot-files"
        assert loc.oci_tag == "server-39-x86_64"
        assert loc.oci_digest == "sha256:" + "a" * 64

    def test_checksum_properties(self):
        """Test checksum-related properties."""
        loc = Location(
            url="https://example.com/file.rpm",
            size=1000,
            checksum="sha256:" + "abcd" * 16,
            local_path="path/to/file.rpm",
        )
        assert loc.checksum_algorithm == "sha256"
        assert loc.checksum_value == "abcd" * 16

    def test_location_serialize(self):
        """Test Location serialization."""
        loc = Location(
            url="https://cdn.example.com/file.rpm",
            size=1849356,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/Packages/b/file.rpm",
        )
        data = loc.serialize()
        assert data["url"] == "https://cdn.example.com/file.rpm"
        assert data["size"] == 1849356
        assert data["checksum"] == "sha256:" + "a" * 64
        assert data["local_path"] == "Server/x86_64/os/Packages/b/file.rpm"
        assert data["contents"] == []

    def test_location_serialize_with_contents(self):
        """Test Location serialization with OCI contents."""
        loc = Location(
            url="oci://quay.io/fedora/boot-files:test@sha256:" + "a" * 64,
            size=101376000,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/images",
            contents=[
                FileEntry(
                    file="pxeboot/vmlinuz",
                    size=11534336,
                    checksum="sha256:" + "b" * 64,
                    layer_digest="sha256:" + "b" * 64,
                ),
                FileEntry(
                    file="pxeboot/initrd.img",
                    size=89478656,
                    checksum="sha256:" + "c" * 64,
                    layer_digest="sha256:" + "c" * 64,
                ),
            ],
        )
        data = loc.serialize()
        assert "contents" in data
        assert len(data["contents"]) == 2
        assert data["contents"][0]["file"] == "pxeboot/vmlinuz"
        assert data["contents"][1]["file"] == "pxeboot/initrd.img"

    def test_location_deserialize(self):
        """Test Location deserialization."""
        data = {
            "url": "https://cdn.example.com/file.rpm",
            "size": 1849356,
            "checksum": "sha256:" + "a" * 64,
            "local_path": "Server/x86_64/os/Packages/b/file.rpm",
        }
        loc = Location.from_dict(data)
        assert loc.url == "https://cdn.example.com/file.rpm"
        assert loc.size == 1849356
        assert loc.local_path == "Server/x86_64/os/Packages/b/file.rpm"
        assert loc.contents == []

    def test_location_deserialize_with_contents(self):
        """Test Location deserialization with OCI contents."""
        data = {
            "url": "oci://quay.io/fedora/boot-files:test@sha256:" + "a" * 64,
            "size": 101376000,
            "checksum": "sha256:" + "a" * 64,
            "local_path": "Server/x86_64/os/images",
            "contents": [
                {
                    "file": "pxeboot/vmlinuz",
                    "size": 11534336,
                    "checksum": "sha256:" + "b" * 64,
                    "layer_digest": "sha256:" + "b" * 64,
                },
            ],
        }
        loc = Location.from_dict(data)
        assert loc.has_contents
        assert len(loc.contents) == 1
        assert loc.contents[0].file == "pxeboot/vmlinuz"

    def test_location_equality(self):
        """Test Location equality comparison."""
        loc1 = Location(
            url="https://example.com/file.rpm",
            size=1000,
            checksum="sha256:" + "a" * 64,
            local_path="path/to/file.rpm",
        )
        loc2 = Location(
            url="https://example.com/file.rpm",
            size=1000,
            checksum="sha256:" + "a" * 64,
            local_path="path/to/file.rpm",
        )
        loc3 = Location(
            url="https://example.com/other.rpm",
            size=1000,
            checksum="sha256:" + "a" * 64,
            local_path="path/to/other.rpm",
        )
        assert loc1 == loc2
        assert loc1 != loc3

    @pytest.mark.parametrize(
        "url, local_path, contents, desc",
        [
            ("/absolute/path/to/file.rpm", "path/to/file.rpm", None, "absolute URL"),
            ("https://example.com/file.rpm", "/absolute/path/to/file.rpm", None, "absolute local_path"),
            ("oci://quay.io/fedora/rpms:bash", "path/to/file.rpm", None, "OCI without digest"),
        ],
    )
    def test_location_validation_errors(self, url, local_path, contents, desc):
        """Test that invalid Location fields are rejected: %s."""
        loc = Location(
            url=url,
            size=1000,
            checksum="sha256:" + "a" * 64,
            local_path=local_path,
            contents=contents,
        )
        with pytest.raises(ValueError):
            loc.validate()

    def test_location_validation_contents_without_oci(self):
        """Test that contents without OCI URL is rejected."""
        loc = Location(
            url="https://example.com/file.rpm",
            size=1000,
            checksum="sha256:" + "a" * 64,
            local_path="path/to/file.rpm",
            contents=[
                FileEntry(
                    file="test.txt",
                    size=100,
                    checksum="sha256:" + "b" * 64,
                    layer_digest="sha256:" + "b" * 64,
                ),
            ],
        )
        with pytest.raises(ValueError):
            loc.validate()

    def test_with_remote_url(self):
        """Test creating a remote URL from a local location."""
        loc = Location(
            url="Server/x86_64/os/Packages/b/bash.rpm",
            size=1000,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/Packages/b/bash.rpm",
        )
        remote = loc.with_remote_url("https://cdn.example.com/compose")
        assert remote.url == "https://cdn.example.com/compose/Server/x86_64/os/Packages/b/bash.rpm"
        assert remote.size == loc.size
        assert remote.checksum == loc.checksum
        assert remote.local_path == loc.local_path

    def test_get_localized_path(self):
        """Test getting the localized filesystem path."""
        loc = Location(
            url="https://example.com/bash.rpm",
            size=1000,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/Packages/b/bash.rpm",
        )
        path = loc.get_localized_path("/mnt/compose")
        assert path == "/mnt/compose/compose/Server/x86_64/os/Packages/b/bash.rpm"

    def test_verify_checksum_success(self):
        """Test successful checksum verification."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test content")
            path = f.name

        try:
            checksum = compute_checksum(path)
            loc = Location(
                url="https://example.com/test.txt",
                size=12,
                checksum=checksum,
                local_path="test.txt",
            )
            assert loc.verify_checksum(path) is True
        finally:
            os.unlink(path)

    def test_verify_checksum_failure(self):
        """Test checksum verification returns False on mismatch."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test content")
            path = f.name

        try:
            loc = Location(
                url="https://example.com/test.txt",
                size=12,
                checksum="sha256:" + "0" * 64,
                local_path="test.txt",
            )
            assert loc.verify_checksum(path) is False
        finally:
            os.unlink(path)

    def test_verify_size_success(self):
        """Test successful size verification."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test content")
            path = f.name

        try:
            loc = Location(
                url="https://example.com/test.txt",
                size=12,
                checksum="sha256:" + "a" * 64,
                local_path="test.txt",
            )
            assert loc.verify_size(path) is True
        finally:
            os.unlink(path)

    def test_verify_size_failure(self):
        """Test size verification returns False on mismatch."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test content")
            path = f.name

        try:
            loc = Location(
                url="https://example.com/test.txt",
                size=999,
                checksum="sha256:" + "a" * 64,
                local_path="test.txt",
            )
            assert loc.verify_size(path) is False
        finally:
            os.unlink(path)

    def test_verify_all_success(self):
        """Test full verification (size + checksum) success."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test content")
            path = f.name

        try:
            checksum = compute_checksum(path)
            loc = Location(
                url="https://example.com/test.txt",
                size=12,
                checksum=checksum,
                local_path="test.txt",
            )
            assert loc.verify(path) is True
        finally:
            os.unlink(path)

    def test_verify_all_failure_size(self):
        """Test full verification returns False when size mismatches."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test content")
            path = f.name

        try:
            checksum = compute_checksum(path)
            loc = Location(
                url="https://example.com/test.txt",
                size=999,
                checksum=checksum,
                local_path="test.txt",
            )
            assert loc.verify(path) is False
        finally:
            os.unlink(path)

    def test_verify_all_failure_checksum(self):
        """Test full verification returns False when checksum mismatches."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(b"test content")
            path = f.name

        try:
            loc = Location(
                url="https://example.com/test.txt",
                size=12,
                checksum="sha256:" + "0" * 64,
                local_path="test.txt",
            )
            assert loc.verify(path) is False
        finally:
            os.unlink(path)

    def test_from_local_file(self):
        """Test creating a Location from a local file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "Packages", "b"))
            filepath = os.path.join(tmpdir, "Packages", "b", "bash.rpm")
            with open(filepath, "wb") as f:
                f.write(b"fake rpm content")

            loc = Location.from_local_file("Packages/b/bash.rpm", tmpdir)
            assert loc.url == "Packages/b/bash.rpm"
            assert loc.local_path == "Packages/b/bash.rpm"
            assert loc.size == 16
            assert loc.checksum.startswith("sha256:")
            loc.validate()

    def test_from_local_file_no_integrity(self):
        """Test creating a Location without computing integrity."""
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "Packages", "b"))
            filepath = os.path.join(tmpdir, "Packages", "b", "bash.rpm")
            with open(filepath, "wb") as f:
                f.write(b"fake rpm content")

            loc = Location.from_local_file("Packages/b/bash.rpm", tmpdir, compute_integrity=False)
            assert loc.url == "Packages/b/bash.rpm"
            assert loc.local_path == "Packages/b/bash.rpm"
            assert loc.size is None
            assert loc.checksum is None
            # Should pass validation -- None size/checksum means "not yet computed"
            loc.validate()


class TestLocationRoundTrip:
    """Test serialization/deserialization round-trips."""

    def test_simple_location_roundtrip(self):
        """Test round-trip for simple HTTPS location."""
        original = Location(
            url="https://cdn.example.com/Packages/bash.rpm",
            size=1849356,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/Packages/b/bash.rpm",
        )
        data = original.serialize()
        restored = Location.from_dict(data)
        assert original == restored

    def test_oci_location_roundtrip(self):
        """Test round-trip for OCI location with contents."""
        original = Location(
            url="oci://quay.io/fedora/boot-files:test@sha256:" + "a" * 64,
            size=101376000,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/images",
            contents=[
                FileEntry(
                    file="pxeboot/vmlinuz",
                    size=11534336,
                    checksum="sha256:" + "b" * 64,
                    layer_digest="sha256:" + "b" * 64,
                ),
                FileEntry(
                    file="pxeboot/initrd.img",
                    size=89478656,
                    checksum="sha256:" + "c" * 64,
                    layer_digest="sha256:" + "c" * 64,
                ),
            ],
        )
        data = original.serialize()
        restored = Location.from_dict(data)
        assert original.url == restored.url
        assert original.size == restored.size
        assert original.checksum == restored.checksum
        assert original.local_path == restored.local_path
        assert len(original.contents) == len(restored.contents)
        assert original.contents[0] == restored.contents[0]
        assert original.contents[1] == restored.contents[1]
