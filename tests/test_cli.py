"""Tests for the productmd CLI tools."""

import json
import os
import sys
from unittest.mock import patch

import pytest

from productmd.cli import load_compose_dir, load_single_file, main
from productmd.cli.progress import _format_filename, _format_size, _format_speed
from productmd.images import Image, Images
from productmd.location import Location
from productmd.rpms import Rpms
from productmd.version import VERSION_1_2, VERSION_2_0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_image(parent, path, size, checksum_hex, img_type="dvd"):
    img = Image(parent)
    img.path = path
    img.mtime = 1738627200
    img.size = size
    img.volume_id = "Test-1.0"
    img.type = img_type
    img.format = "iso"
    img.arch = "x86_64"
    img.disc_number = 1
    img.disc_count = 1
    img.checksums = {"sha256": checksum_hex}
    img.subvariant = "Server"
    return img


def _create_v12_compose(compose_dir):
    """Create a minimal v1.2 compose directory with metadata files."""
    metadata_dir = os.path.join(compose_dir, "metadata")
    os.makedirs(metadata_dir, exist_ok=True)

    im = Images()
    im.header.version = "1.2"
    im.compose.id = "Test-1.0-20260204.0"
    im.compose.type = "production"
    im.compose.date = "20260204"
    im.compose.respin = 0
    im.output_version = VERSION_1_2

    boot = _make_image(im, "Server/x86_64/iso/boot.iso", 512000000, "a" * 64, "boot")
    im.add("Server", "x86_64", boot)
    im.dump(os.path.join(metadata_dir, "images.json"))

    rpms = Rpms()
    rpms.header.version = "1.2"
    rpms.compose.id = "Test-1.0-20260204.0"
    rpms.compose.type = "production"
    rpms.compose.date = "20260204"
    rpms.compose.respin = 0
    rpms.output_version = VERSION_1_2

    rpms.add(
        variant="Server",
        arch="x86_64",
        nevra="bash-0:5.2.26-3.fc41.x86_64",
        path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
        sigkey="a15b79cc",
        srpm_nevra="bash-0:5.2.26-3.fc41.src",
        category="binary",
    )
    rpms.dump(os.path.join(metadata_dir, "rpms.json"))

    return compose_dir


def _create_v20_compose(compose_dir):
    """Create a minimal v2.0 compose directory with metadata files."""
    metadata_dir = os.path.join(compose_dir, "metadata")
    os.makedirs(metadata_dir, exist_ok=True)

    im = Images()
    im.header.version = "2.0"
    im.compose.id = "Test-1.0-20260204.0"
    im.compose.type = "production"
    im.compose.date = "20260204"
    im.compose.respin = 0
    im.output_version = VERSION_2_0

    boot = _make_image(im, "Server/x86_64/iso/boot.iso", 512000000, "a" * 64, "boot")
    boot.location = Location(
        url="https://cdn.example.com/Server/x86_64/iso/boot.iso",
        size=512000000,
        checksum="sha256:" + "a" * 64,
        local_path="Server/x86_64/iso/boot.iso",
    )
    im.add("Server", "x86_64", boot)
    im.dump(os.path.join(metadata_dir, "images.json"))

    return compose_dir


def _run_cli(*args):
    """Run CLI with given arguments, return exit code."""
    with patch.object(sys, "argv", ["productmd"] + list(args)):
        try:
            main()
            return 0
        except SystemExit as e:
            return e.code if e.code is not None else 0


# ---------------------------------------------------------------------------
# Tests: load functions
# ---------------------------------------------------------------------------


class TestLoadFunctions:
    """Tests for the load_single_file and load_compose_dir utilities."""

    def test_load_from_compose_dir(self, tmp_path):
        """Test loading metadata from a compose directory."""
        compose_dir = str(tmp_path / "compose")
        _create_v12_compose(compose_dir)

        metadata, compose_path = load_compose_dir(str(tmp_path))
        assert "images" in metadata
        assert "rpms" in metadata
        assert compose_path == compose_dir

    def test_load_single_file(self, tmp_path):
        """Test loading a single metadata file."""
        compose_dir = str(tmp_path / "compose")
        _create_v12_compose(compose_dir)

        metadata = load_single_file(os.path.join(compose_dir, "metadata", "images.json"))
        assert "images" in metadata
        assert "rpms" not in metadata

    def test_load_single_file_missing_raises(self, tmp_path):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_single_file(str(tmp_path / "nonexistent.json"))

    def test_load_compose_dir_missing_raises(self, tmp_path):
        """Test that missing directory raises NotADirectoryError."""
        with pytest.raises(NotADirectoryError):
            load_compose_dir(str(tmp_path / "nonexistent"))


# ---------------------------------------------------------------------------
# Tests: productmd upgrade
# ---------------------------------------------------------------------------


class TestUpgradeCommand:
    """Tests for the productmd upgrade subcommand."""

    def test_basic_upgrade(self, tmp_path):
        """Test basic upgrade writes v2.0 metadata."""
        compose_dir = str(tmp_path / "compose")
        _create_v12_compose(compose_dir)
        output_dir = str(tmp_path / "output")

        exit_code = _run_cli(
            "upgrade",
            "--output",
            output_dir,
            "--base-url",
            "https://cdn.example.com/",
            str(tmp_path),
        )

        assert exit_code == 0
        assert os.path.isfile(os.path.join(output_dir, "images.json"))
        assert os.path.isfile(os.path.join(output_dir, "rpms.json"))

        with open(os.path.join(output_dir, "images.json")) as f:
            data = json.load(f)
        assert data["header"]["version"] == "2.0"

    def test_upgrade_with_base_url(self, tmp_path):
        """Test that URLs include base_url prefix."""
        compose_dir = str(tmp_path / "compose")
        _create_v12_compose(compose_dir)
        output_dir = str(tmp_path / "output")

        _run_cli(
            "upgrade",
            "--output",
            output_dir,
            "--base-url",
            "https://cdn.example.com/",
            str(tmp_path),
        )

        with open(os.path.join(output_dir, "images.json")) as f:
            data = json.load(f)

        images = data["payload"]["images"]["Server"]["x86_64"]
        for img in images:
            assert img["location"]["url"].startswith("https://cdn.example.com/")

    def test_upgrade_with_url_map(self, tmp_path):
        """Test upgrade with per-type URL mapping."""
        compose_dir = str(tmp_path / "compose")
        _create_v12_compose(compose_dir)
        output_dir = str(tmp_path / "output")

        url_map = {"image": "https://images.cdn/{path}", "default": "https://cdn/{path}"}
        url_map_file = str(tmp_path / "url-map.json")
        with open(url_map_file, "w") as f:
            json.dump(url_map, f)

        _run_cli(
            "upgrade",
            "--output",
            output_dir,
            "--url-map",
            url_map_file,
            str(tmp_path),
        )

        with open(os.path.join(output_dir, "images.json")) as f:
            data = json.load(f)

        images = data["payload"]["images"]["Server"]["x86_64"]
        for img in images:
            assert img["location"]["url"].startswith("https://images.cdn/")

    def test_upgrade_single_file(self, tmp_path):
        """Test upgrading a single metadata file."""
        compose_dir = str(tmp_path / "compose")
        _create_v12_compose(compose_dir)
        output_dir = str(tmp_path / "output")

        exit_code = _run_cli(
            "upgrade",
            "--output",
            output_dir,
            "--base-url",
            "https://cdn.example.com/",
            os.path.join(compose_dir, "metadata", "images.json"),
        )

        assert exit_code == 0
        assert os.path.isfile(os.path.join(output_dir, "images.json"))
        assert not os.path.exists(os.path.join(output_dir, "rpms.json"))

    def test_upgrade_missing_args_exits(self):
        """Test that missing required args exits with code 2."""
        exit_code = _run_cli("upgrade")
        assert exit_code == 2

    def test_upgrade_url_rejected(self):
        """Test that HTTP URLs are rejected."""
        exit_code = _run_cli(
            "upgrade",
            "--output",
            "/tmp/out",
            "--base-url",
            "https://cdn/",
            "http://cdn.example.com/compose",
        )
        assert exit_code == 1

    def test_upgrade_https_url_rejected(self):
        """Test that HTTPS URLs are also rejected."""
        exit_code = _run_cli(
            "upgrade",
            "--output",
            "/tmp/out",
            "--base-url",
            "https://cdn/",
            "https://cdn.example.com/compose/metadata/images.json",
        )
        assert exit_code == 1

    def test_upgrade_compute_checksums_without_compose_root_exits(self, tmp_path):
        """Test that --compute-checksums without a discoverable compose root exits with error."""
        # Create a loose metadata file outside any compose structure
        images_file = str(tmp_path / "images.json")
        with open(images_file, "w") as f:
            json.dump(
                {
                    "header": {"type": "productmd.images", "version": "1.2"},
                    "payload": {
                        "compose": {"id": "Test-1.0-20260204.0", "type": "production", "date": "20260204", "respin": 0},
                        "images": {},
                    },
                },
                f,
            )

        exit_code = _run_cli(
            "upgrade",
            "--output",
            str(tmp_path / "out"),
            "--base-url",
            "https://cdn/",
            "--compute-checksums",
            images_file,
        )
        assert exit_code == 1

    def test_upgrade_invalid_url_map(self, tmp_path):
        """Test that invalid url-map JSON exits with error."""
        compose_dir = str(tmp_path / "compose")
        _create_v12_compose(compose_dir)
        output_dir = str(tmp_path / "output")

        url_map_file = str(tmp_path / "bad-url-map.json")
        with open(url_map_file, "w") as f:
            f.write("not valid json{{{")

        exit_code = _run_cli(
            "upgrade",
            "--output",
            output_dir,
            "--url-map",
            url_map_file,
            str(tmp_path),
        )
        assert exit_code == 1


# ---------------------------------------------------------------------------
# Tests: productmd downgrade
# ---------------------------------------------------------------------------


class TestDowngradeCommand:
    """Tests for the productmd downgrade subcommand."""

    def test_basic_downgrade(self, tmp_path):
        """Test basic downgrade writes v1.2 metadata."""
        compose_dir = str(tmp_path / "compose")
        _create_v20_compose(compose_dir)
        output_dir = str(tmp_path / "output")

        exit_code = _run_cli(
            "downgrade",
            "--output",
            output_dir,
            str(tmp_path),
        )

        assert exit_code == 0
        assert os.path.isfile(os.path.join(output_dir, "images.json"))

        with open(os.path.join(output_dir, "images.json")) as f:
            data = json.load(f)
        assert data["header"]["version"] == "1.2"

        images = data["payload"]["images"]["Server"]["x86_64"]
        for img in images:
            assert "path" in img
            assert "location" not in img

    def test_downgrade_missing_args_exits(self):
        """Test that missing required args exits with code 2."""
        exit_code = _run_cli("downgrade")
        assert exit_code == 2

    def test_downgrade_preserves_paths(self, tmp_path):
        """Test that downgrade preserves local_path as v1.2 path."""
        compose_dir = str(tmp_path / "compose")
        _create_v20_compose(compose_dir)
        output_dir = str(tmp_path / "output")

        _run_cli(
            "downgrade",
            "--output",
            output_dir,
            os.path.join(compose_dir, "metadata", "images.json"),
        )

        with open(os.path.join(output_dir, "images.json")) as f:
            data = json.load(f)

        images = data["payload"]["images"]["Server"]["x86_64"]
        paths = [img["path"] for img in images]
        assert "Server/x86_64/iso/boot.iso" in paths

    def test_downgrade_url_rejected(self):
        """Test that remote URLs are rejected for downgrade."""
        exit_code = _run_cli(
            "downgrade",
            "--output",
            "/tmp/out",
            "https://cdn.example.com/compose/metadata/images.json",
        )
        assert exit_code == 1


# ---------------------------------------------------------------------------
# Tests: productmd localize
# ---------------------------------------------------------------------------


class TestLocalizeCommand:
    """Tests for the productmd localize subcommand."""

    @patch("productmd.localize.urllib.request.urlopen")
    def test_basic_localize(self, mock_urlopen, tmp_path):
        """Test basic localization downloads files."""
        import io
        from unittest.mock import MagicMock

        response = MagicMock()
        response.read = io.BytesIO(b"iso content").read
        response.headers = {"Content-Length": "11"}
        mock_urlopen.return_value = response

        compose_dir = str(tmp_path / "compose")
        _create_v20_compose(compose_dir)
        output_dir = str(tmp_path / "output")

        exit_code = _run_cli(
            "localize",
            "--output",
            output_dir,
            "--parallel-downloads",
            "1",
            "--no-verify-checksums",
            "--retries",
            "0",
            os.path.join(compose_dir, "metadata", "images.json"),
        )

        assert exit_code == 0

    @patch("productmd.localize.urllib.request.urlopen")
    def test_localize_with_compose_dir(self, mock_urlopen, tmp_path):
        """Test localization using a compose directory as input."""
        import io
        from unittest.mock import MagicMock

        response = MagicMock()
        response.read = io.BytesIO(b"iso content").read
        response.headers = {"Content-Length": "11"}
        mock_urlopen.return_value = response

        compose_dir = str(tmp_path / "compose")
        _create_v20_compose(compose_dir)
        output_dir = str(tmp_path / "output")

        exit_code = _run_cli(
            "localize",
            "--output",
            output_dir,
            "--parallel-downloads",
            "1",
            "--no-verify-checksums",
            "--retries",
            "0",
            str(tmp_path),
        )

        assert exit_code == 0

    def test_localize_missing_args_exits(self):
        """Test that missing required args exits with code 2."""
        exit_code = _run_cli("localize")
        assert exit_code == 2

    def test_localize_url_rejected(self):
        """Test that remote URLs are rejected for localize."""
        exit_code = _run_cli(
            "localize",
            "--output",
            "/tmp/out",
            "http://cdn.example.com/compose/metadata/images.json",
        )
        assert exit_code == 1


# ---------------------------------------------------------------------------
# Tests: productmd verify
# ---------------------------------------------------------------------------


class TestVerifyCommand:
    """Tests for the productmd verify subcommand."""

    def test_verify_quick_mode(self, tmp_path):
        """Test that --quick only verifies metadata loads."""
        compose_dir = str(tmp_path / "compose")
        _create_v12_compose(compose_dir)

        exit_code = _run_cli(
            "verify",
            "--quick",
            str(tmp_path),
        )

        assert exit_code == 0

    def test_verify_with_report(self, tmp_path):
        """Test that --report writes a JSON report file."""
        compose_dir = str(tmp_path / "compose")
        _create_v12_compose(compose_dir)
        report_file = str(tmp_path / "report.json")

        _run_cli(
            "verify",
            "--quick",
            "--report",
            report_file,
            str(tmp_path),
        )

        assert os.path.isfile(report_file)
        with open(report_file) as f:
            report = json.load(f)
        assert "verified" in report
        assert "failed" in report
        assert "skipped" in report

    def test_verify_local_files(self, tmp_path):
        """Test verification of local files with v2.0 checksums."""
        compose_dir = str(tmp_path / "compose")
        _create_v20_compose(compose_dir)

        iso_dir = os.path.join(compose_dir, "Server", "x86_64", "iso")
        os.makedirs(iso_dir, exist_ok=True)
        with open(os.path.join(iso_dir, "boot.iso"), "wb") as f:
            f.write(b"fake iso content")

        exit_code = _run_cli(
            "verify",
            str(tmp_path),
        )

        # Exit code 1 because checksum mismatch
        assert exit_code == 1

    def test_verify_missing_args_exits(self):
        """Test that missing required args exits with code 2."""
        exit_code = _run_cli("verify")
        assert exit_code == 2

    def test_verify_single_file_skips_artifacts(self, tmp_path):
        """Test that verify with a file outside any compose skips artifact verification."""
        # Create a loose metadata file outside any compose structure
        images_file = str(tmp_path / "images.json")
        with open(images_file, "w") as f:
            json.dump(
                {
                    "header": {"type": "productmd.images", "version": "2.0"},
                    "payload": {
                        "compose": {"id": "Test-1.0-20260204.0", "type": "production", "date": "20260204", "respin": 0},
                        "images": {},
                    },
                },
                f,
            )

        # No compose root discoverable — should skip artifact verification
        exit_code = _run_cli(
            "verify",
            images_file,
        )

        # Should exit 0 (no checksum verification attempted)
        assert exit_code == 0

    def test_verify_url_rejected(self):
        """Test that remote URLs are rejected for verify."""
        exit_code = _run_cli(
            "verify",
            "https://cdn.example.com/compose/metadata/images.json",
        )
        assert exit_code == 1


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Tests for CLI error handling and edge cases."""

    def test_compose_dir_not_found(self, tmp_path):
        """Test non-existent path exits with error."""
        exit_code = _run_cli(
            "upgrade",
            "--output",
            str(tmp_path / "out"),
            "--base-url",
            "https://cdn/",
            str(tmp_path / "nonexistent"),
        )
        assert exit_code == 1

    def test_single_file_not_found(self, tmp_path):
        """Test non-existent single file exits with error."""
        exit_code = _run_cli(
            "upgrade",
            "--output",
            str(tmp_path / "out"),
            "--base-url",
            "https://cdn/",
            str(tmp_path / "nonexistent.json"),
        )
        assert exit_code == 1


# ---------------------------------------------------------------------------
# Tests: no subcommand
# ---------------------------------------------------------------------------


class TestNoSubcommand:
    """Tests for running productmd without a subcommand."""

    def test_no_subcommand_exits(self):
        """Test that running without a subcommand exits with code 1."""
        exit_code = _run_cli()
        assert exit_code == 1


# ---------------------------------------------------------------------------
# Tests: progress display utilities
# ---------------------------------------------------------------------------


class TestFormatFilename:
    """Tests for _format_filename path truncation."""

    @pytest.mark.parametrize(
        "path,expected_width",
        [
            ("Server/x86_64/os/GPL", 50),
            ("Server/x86_64/iso/boot.iso", 50),
            ("Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm", 50),
            ("Workstation/x86_64/iso/Fedora-Workstation-Live-x86_64-41-1.0.iso", 50),
        ],
    )
    def test_output_width_is_fixed(self, path, expected_width):
        """Test that output is always exactly max_width characters."""
        result = _format_filename(path)
        assert len(result) == expected_width

    def test_short_path_no_truncation(self):
        """Test that short paths are padded but not truncated."""
        result = _format_filename("Server/x86_64/os/GPL")
        assert result.startswith("Server/x86_64/os/GPL")
        assert result == "Server/x86_64/os/GPL".ljust(50)

    def test_long_path_truncated_at_slash(self):
        """Test that long paths are truncated at / boundaries."""
        result = _format_filename("Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm")
        # Should contain /.../ separator
        assert "/.../" + "" in result
        # Should preserve the basename
        assert "bash-5.2.26-3.fc41.x86_64.rpm" in result
        # Should preserve some prefix
        assert result.startswith("Server")

    def test_very_long_basename(self):
        """Test that very long basenames are truncated with leading ..."""
        long_name = "a" * 60 + ".rpm"
        result = _format_filename(f"Server/{long_name}")
        assert result.startswith("...")
        assert result.rstrip().endswith(".rpm")
        assert len(result) == 50

    def test_no_slash_in_path(self):
        """Test path with no / separator."""
        result = _format_filename("just-a-filename.json")
        assert result.startswith("just-a-filename.json")
        assert len(result) == 50

    def test_custom_max_width(self):
        """Test with custom max_width parameter."""
        result = _format_filename("Server/x86_64/os/GPL", max_width=30)
        assert len(result) == 30


class TestFormatSize:
    """Tests for _format_size byte formatting."""

    @pytest.mark.parametrize(
        "n,expected",
        [
            (0, "0B"),
            (512, "512B"),
            (1000, "1kB"),
            (1500, "1.5kB"),
            (1000000, "1MB"),
            (512000000, "512MB"),
            (1234567890, "1.2GB"),
            (2465792000, "2.5GB"),
            (None, "?B"),
        ],
    )
    def test_format_size(self, n, expected):
        """Test byte count formatting."""
        result = _format_size(n)
        assert result == expected

    def test_format_size_terabytes(self):
        """Test formatting of terabyte values."""
        result = _format_size(1000000000000)
        assert result == "1TB"


class TestFormatSpeed:
    """Tests for _format_speed download speed formatting."""

    def test_format_speed_bytes(self):
        """Test speed in bytes per second."""
        result = _format_speed(500)
        assert result == "500B/s"

    def test_format_speed_megabytes(self):
        """Test speed in megabytes per second."""
        result = _format_speed(5000000)
        assert result == "5MB/s"

    def test_format_speed_gigabytes(self):
        """Test speed in gigabytes per second."""
        result = _format_speed(2500000000)
        assert result == "2.5GB/s"
