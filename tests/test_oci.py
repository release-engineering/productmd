"""Tests for OCI image download and extraction utilities."""

import hashlib
import io
import json
import os
import tarfile
from unittest.mock import MagicMock, patch

import pytest

oras = pytest.importorskip("oras", reason="oras-py not installed")

from productmd.oci import (  # noqa: E402
    find_layer_blob,
    get_downloader,
    parse_oci_index,
    parse_oci_manifest,
)


# ---------------------------------------------------------------------------
# Helpers: create mock OCI layout directories
# ---------------------------------------------------------------------------


def _sha256_hex(data):
    """Compute sha256 hex digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def _create_tar_gz(tmp_path, files, name="layer"):
    """Create a gzipped tar file containing the given files.

    :param files: dict of {path: content_bytes}
    :return: (path_to_tar_gz, sha256_digest)
    """
    tar_path = str(tmp_path / f"{name}.tar.gz")
    with tarfile.open(tar_path, "w:gz") as tar:
        for file_path, content in files.items():
            info = tarfile.TarInfo(name=file_path)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))

    with open(tar_path, "rb") as f:
        digest = _sha256_hex(f.read())

    return tar_path, digest


def _create_oci_layout(tmp_path, layers):
    """Create a minimal OCI layout directory.

    :param layers: list of (layer_digest, layer_blob_path) tuples
    :return: path to image directory
    """
    image_dir = str(tmp_path / "image")
    blobs_dir = os.path.join(image_dir, "blobs", "sha256")
    os.makedirs(blobs_dir)

    # Create layer blob copies
    layer_descriptors = []
    for layer_digest, layer_path in layers:
        blob_dest = os.path.join(blobs_dir, layer_digest)
        with open(layer_path, "rb") as src:
            with open(blob_dest, "wb") as dst:
                dst.write(src.read())
        layer_descriptors.append(
            {
                "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
                "digest": f"sha256:{layer_digest}",
                "size": os.path.getsize(blob_dest),
            }
        )

    # Create manifest
    manifest = {
        "schemaVersion": 2,
        "mediaType": "application/vnd.oci.image.manifest.v1+json",
        "config": {
            "mediaType": "application/vnd.oci.image.config.v1+json",
            "digest": "sha256:" + "0" * 64,
            "size": 0,
        },
        "layers": layer_descriptors,
    }
    manifest_bytes = json.dumps(manifest).encode()
    manifest_digest = _sha256_hex(manifest_bytes)
    with open(os.path.join(blobs_dir, manifest_digest), "wb") as f:
        f.write(manifest_bytes)

    # Create empty config blob
    with open(os.path.join(blobs_dir, "0" * 64), "w") as f:
        json.dump({}, f)

    # Create index.json
    index = {
        "schemaVersion": 2,
        "manifests": [
            {
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
                "digest": f"sha256:{manifest_digest}",
                "size": len(manifest_bytes),
            }
        ],
    }
    with open(os.path.join(image_dir, "index.json"), "w") as f:
        json.dump(index, f)

    # Create oci-layout file
    with open(os.path.join(image_dir, "oci-layout"), "w") as f:
        json.dump({"imageLayoutVersion": "1.0.0"}, f)

    return image_dir


# ---------------------------------------------------------------------------
# Tests: OrasPyDownloader
# ---------------------------------------------------------------------------


class TestOrasPyDownloader:
    """Tests for the OrasPyDownloader class."""

    @patch("productmd.oci.HAS_ORAS", False)
    def test_oras_not_installed_raises(self):
        """Test that missing oras-py raises RuntimeError."""
        from productmd.oci import OrasPyDownloader

        with pytest.raises(RuntimeError, match="oras-py is required"):
            OrasPyDownloader()

    @patch("productmd.oci.oras.client.OrasClient")
    def test_download_calls_client_pull(self, mock_client_cls, tmp_path):
        """Test that download calls client.pull with correct arguments."""
        from productmd.oci import OrasPyDownloader

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        downloader = OrasPyDownloader()
        dest = str(tmp_path / "output")
        downloader.download("oci://quay.io/fedora/rpms:tag@sha256:" + "a" * 64, dest)

        mock_client.pull.assert_called_once()
        call_kwargs = mock_client.pull.call_args
        assert call_kwargs[1]["target"] == "quay.io/fedora/rpms:tag@sha256:" + "a" * 64
        assert call_kwargs[1]["outdir"] == dest

    @patch("productmd.oci.oras.client.OrasClient")
    def test_download_strips_oci_prefix(self, mock_client_cls):
        """Test that oci:// prefix is stripped from the URL."""
        from productmd.oci import OrasPyDownloader

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        downloader = OrasPyDownloader()
        downloader.download("oci://registry.example.com/repo@sha256:" + "b" * 64, "/tmp/out")

        target = mock_client.pull.call_args[1]["target"]
        assert not target.startswith("oci://")
        assert target == "registry.example.com/repo@sha256:" + "b" * 64

    @patch("productmd.oci.oras.client.OrasClient")
    def test_download_and_extract_without_contents(self, mock_client_cls, tmp_path):
        """Test download_and_extract without contents calls download (simple pull)."""
        from productmd.oci import OrasPyDownloader

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        downloader = OrasPyDownloader()
        dest = str(tmp_path / "output")
        downloader.download_and_extract("oci://registry/repo@sha256:" + "c" * 64, dest)

        mock_client.pull.assert_called_once()

    @patch("productmd.oci.oras.client.OrasClient")
    @patch("productmd.oci.oras.provider.Registry")
    def test_download_and_extract_with_contents(self, mock_registry_cls, mock_client_cls, tmp_path):
        """Test download_and_extract with contents calls extract_contents."""
        from productmd.location import FileEntry
        from productmd.oci import OrasPyDownloader

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_registry = MagicMock()
        mock_registry_cls.return_value = mock_registry

        # Mock download_blob to write raw file content (not tar)
        def write_blob(container, digest, outfile):
            os.makedirs(os.path.dirname(outfile) or ".", exist_ok=True)
            with open(outfile, "wb") as f:
                f.write(b"raw file content")

        mock_registry.download_blob.side_effect = write_blob

        contents = [
            FileEntry(file="vmlinuz", size=16, checksum=None, layer_digest="sha256:" + "d" * 64),
        ]

        downloader = OrasPyDownloader()
        dest = str(tmp_path / "output")
        downloader.download_and_extract("oci://registry/repo@sha256:" + "e" * 64, dest, contents=contents)

        # Should NOT have called client.pull (that's for simple downloads)
        mock_client.pull.assert_not_called()
        # Should have called registry.download_blob
        mock_registry.download_blob.assert_called_once()

        # File should exist
        assert os.path.isfile(os.path.join(dest, "vmlinuz"))


# ---------------------------------------------------------------------------
# Tests: extract_contents — tar rejection and checksum
# ---------------------------------------------------------------------------


class TestExtractContents:
    """Tests for extract_contents with ORAS blobs and tar rejection."""

    @patch("productmd.oci.oras.client.OrasClient")
    @patch("productmd.oci.oras.provider.Registry")
    def test_extract_contents_raw_blob(self, mock_registry_cls, mock_client_cls, tmp_path):
        """Test that raw ORAS blobs are downloaded directly."""
        from productmd.location import FileEntry
        from productmd.oci import OrasPyDownloader

        mock_client_cls.return_value = MagicMock()
        mock_registry = MagicMock()
        mock_registry_cls.return_value = mock_registry

        content = b"raw kernel binary"

        def write_blob(container, digest, outfile):
            os.makedirs(os.path.dirname(outfile) or ".", exist_ok=True)
            with open(outfile, "wb") as f:
                f.write(content)

        mock_registry.download_blob.side_effect = write_blob

        contents = [
            FileEntry(file="pxeboot/vmlinuz", size=len(content), checksum=None, layer_digest="sha256:" + "a" * 64),
        ]

        dest_dir = str(tmp_path / "extracted")
        downloader = OrasPyDownloader()
        downloader.extract_contents("oci://registry/repo@sha256:" + "b" * 64, contents, dest_dir)

        result_path = os.path.join(dest_dir, "pxeboot", "vmlinuz")
        assert os.path.isfile(result_path)
        with open(result_path, "rb") as f:
            assert f.read() == content

    @patch("productmd.oci.oras.client.OrasClient")
    @patch("productmd.oci.oras.provider.Registry")
    def test_extract_contents_tar_blob_raises(self, mock_registry_cls, mock_client_cls, tmp_path):
        """Test that tar.gz container image layers are rejected."""
        from productmd.location import FileEntry
        from productmd.oci import OrasPyDownloader

        mock_client_cls.return_value = MagicMock()
        mock_registry = MagicMock()
        mock_registry_cls.return_value = mock_registry

        # Create a real tar.gz blob
        tar_path, _ = _create_tar_gz(tmp_path, {"file.txt": b"content"})

        def write_tar_blob(container, digest, outfile):
            os.makedirs(os.path.dirname(outfile) or ".", exist_ok=True)
            with open(tar_path, "rb") as src:
                with open(outfile, "wb") as dst:
                    dst.write(src.read())

        mock_registry.download_blob.side_effect = write_tar_blob

        contents = [
            FileEntry(file="file.txt", size=7, checksum=None, layer_digest="sha256:" + "c" * 64),
        ]

        dest_dir = str(tmp_path / "extracted")
        downloader = OrasPyDownloader()

        with pytest.raises(ValueError, match="tar archive.*ORAS-compatible raw file blobs"):
            downloader.extract_contents("oci://registry/repo@sha256:" + "d" * 64, contents, dest_dir)

    @patch("productmd.oci.oras.client.OrasClient")
    @patch("productmd.oci.oras.provider.Registry")
    def test_extract_contents_verifies_checksum(self, mock_registry_cls, mock_client_cls, tmp_path):
        """Test that correct checksum passes verification."""
        from productmd.location import FileEntry, compute_checksum as cc
        from productmd.oci import OrasPyDownloader

        mock_client_cls.return_value = MagicMock()
        mock_registry = MagicMock()
        mock_registry_cls.return_value = mock_registry

        content = b"file with correct checksum"

        # Compute checksum of the content
        tmp_file = tmp_path / "tmp_content"
        tmp_file.write_bytes(content)
        correct_checksum = cc(str(tmp_file), "sha256")

        def write_blob(container, digest, outfile):
            os.makedirs(os.path.dirname(outfile) or ".", exist_ok=True)
            with open(outfile, "wb") as f:
                f.write(content)

        mock_registry.download_blob.side_effect = write_blob

        contents = [
            FileEntry(file="file.txt", size=len(content), checksum=correct_checksum, layer_digest="sha256:" + "e" * 64),
        ]

        dest_dir = str(tmp_path / "extracted")
        downloader = OrasPyDownloader()
        downloader.extract_contents("oci://registry/repo@sha256:" + "f" * 64, contents, dest_dir)

        assert os.path.isfile(os.path.join(dest_dir, "file.txt"))

    @patch("productmd.oci.oras.client.OrasClient")
    @patch("productmd.oci.oras.provider.Registry")
    def test_extract_contents_checksum_mismatch_raises(self, mock_registry_cls, mock_client_cls, tmp_path):
        """Test that wrong checksum raises ValueError."""
        from productmd.location import FileEntry
        from productmd.oci import OrasPyDownloader

        mock_client_cls.return_value = MagicMock()
        mock_registry = MagicMock()
        mock_registry_cls.return_value = mock_registry

        def write_blob(container, digest, outfile):
            os.makedirs(os.path.dirname(outfile) or ".", exist_ok=True)
            with open(outfile, "wb") as f:
                f.write(b"file content")

        mock_registry.download_blob.side_effect = write_blob

        contents = [
            FileEntry(
                file="file.txt",
                size=12,
                checksum="sha256:" + "f" * 64,  # wrong checksum
                layer_digest="sha256:" + "a" * 64,
            ),
        ]

        dest_dir = str(tmp_path / "extracted")
        downloader = OrasPyDownloader()

        with pytest.raises(ValueError, match="Checksum mismatch"):
            downloader.extract_contents("oci://registry/repo@sha256:" + "b" * 64, contents, dest_dir)


# ---------------------------------------------------------------------------
# Tests: OCI layout parsing utilities
# ---------------------------------------------------------------------------


class TestOciLayoutParsing:
    """Tests for OCI index and manifest parsing."""

    def test_parse_oci_index(self, tmp_path):
        """Test parsing index.json returns manifest descriptors."""
        layer_path, layer_digest = _create_tar_gz(tmp_path, {"file.txt": b"hello"})
        image_dir = _create_oci_layout(tmp_path, [(layer_digest, layer_path)])

        manifests = parse_oci_index(image_dir)

        assert len(manifests) == 1
        assert manifests[0]["digest"].startswith("sha256:")
        assert manifests[0]["mediaType"] == "application/vnd.oci.image.manifest.v1+json"

    def test_parse_oci_manifest(self, tmp_path):
        """Test parsing manifest returns layers."""
        layer_path, layer_digest = _create_tar_gz(tmp_path, {"file.txt": b"hello"})
        image_dir = _create_oci_layout(tmp_path, [(layer_digest, layer_path)])

        manifests = parse_oci_index(image_dir)
        manifest = parse_oci_manifest(image_dir, manifests[0]["digest"])

        assert "layers" in manifest
        assert len(manifest["layers"]) == 1
        assert manifest["layers"][0]["digest"] == f"sha256:{layer_digest}"

    def test_find_layer_blob_missing_raises(self, tmp_path):
        """Test that missing layer blob raises ValueError."""
        layer_path, layer_digest = _create_tar_gz(tmp_path, {"file.txt": b"hello"})
        image_dir = _create_oci_layout(tmp_path, [(layer_digest, layer_path)])

        with pytest.raises(ValueError, match="Layer blob not found"):
            find_layer_blob(image_dir, "sha256:" + "f" * 64)


# ---------------------------------------------------------------------------
# Tests: get_downloader factory
# ---------------------------------------------------------------------------


class TestGetDownloader:
    """Tests for the get_downloader factory function."""

    def test_get_downloader_returns_instance(self):
        """Test that get_downloader returns a working downloader."""
        from productmd.oci import OrasPyDownloader

        downloader = get_downloader()
        assert isinstance(downloader, OrasPyDownloader)

    @patch("productmd.oci.HAS_ORAS", False)
    def test_get_downloader_no_oras_raises(self):
        """Test that get_downloader raises when oras-py is not installed."""
        with pytest.raises(RuntimeError, match="oras-py is required"):
            get_downloader()


# ---------------------------------------------------------------------------
# Tests: _get_auth_configs — Podman/Docker credential discovery
# ---------------------------------------------------------------------------


class TestGetAuthConfigs:
    """Tests for OrasPyDownloader._get_auth_configs credential discovery."""

    @patch("productmd.oci.oras.client.OrasClient")
    def test_no_auth_files_returns_empty(self, mock_client_cls, tmp_path, monkeypatch):
        """Test that missing auth files return empty list."""
        from productmd.oci import OrasPyDownloader

        mock_client_cls.return_value = MagicMock()
        monkeypatch.delenv("REGISTRY_AUTH_FILE", raising=False)
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        monkeypatch.delenv("DOCKER_CONFIG", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path / "nonexistent"))

        downloader = OrasPyDownloader()
        configs = downloader._get_auth_configs()
        assert configs == []

    @patch("productmd.oci.oras.client.OrasClient")
    def test_registry_auth_file_env(self, mock_client_cls, tmp_path, monkeypatch):
        """Test that $REGISTRY_AUTH_FILE is discovered."""
        from productmd.oci import OrasPyDownloader

        mock_client_cls.return_value = MagicMock()
        auth_file = tmp_path / "auth.json"
        auth_file.write_text('{"auths": {}}')
        monkeypatch.setenv("REGISTRY_AUTH_FILE", str(auth_file))
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        monkeypatch.delenv("DOCKER_CONFIG", raising=False)

        downloader = OrasPyDownloader()
        configs = downloader._get_auth_configs()
        assert str(auth_file) in configs

    @patch("productmd.oci.oras.client.OrasClient")
    def test_xdg_runtime_dir(self, mock_client_cls, tmp_path, monkeypatch):
        """Test that $XDG_RUNTIME_DIR/containers/auth.json is discovered."""
        from productmd.oci import OrasPyDownloader

        mock_client_cls.return_value = MagicMock()
        containers_dir = tmp_path / "containers"
        containers_dir.mkdir()
        auth_file = containers_dir / "auth.json"
        auth_file.write_text('{"auths": {}}')
        monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
        monkeypatch.delenv("REGISTRY_AUTH_FILE", raising=False)
        monkeypatch.delenv("DOCKER_CONFIG", raising=False)

        downloader = OrasPyDownloader()
        configs = downloader._get_auth_configs()
        assert str(auth_file) in configs

    @patch("productmd.oci.oras.client.OrasClient")
    def test_docker_config_env(self, mock_client_cls, tmp_path, monkeypatch):
        """Test that $DOCKER_CONFIG/config.json is discovered."""
        from productmd.oci import OrasPyDownloader

        mock_client_cls.return_value = MagicMock()
        config_file = tmp_path / "config.json"
        config_file.write_text('{"auths": {}}')
        monkeypatch.setenv("DOCKER_CONFIG", str(tmp_path))
        monkeypatch.delenv("REGISTRY_AUTH_FILE", raising=False)
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)

        downloader = OrasPyDownloader()
        configs = downloader._get_auth_configs()
        assert str(config_file) in configs

    @patch("productmd.oci.oras.client.OrasClient")
    def test_multiple_sources_discovered(self, mock_client_cls, tmp_path, monkeypatch):
        """Test that multiple auth sources are all discovered."""
        from productmd.oci import OrasPyDownloader

        mock_client_cls.return_value = MagicMock()

        # Create REGISTRY_AUTH_FILE
        reg_auth = tmp_path / "podman-auth.json"
        reg_auth.write_text('{"auths": {}}')
        monkeypatch.setenv("REGISTRY_AUTH_FILE", str(reg_auth))

        # Create DOCKER_CONFIG
        docker_dir = tmp_path / "docker"
        docker_dir.mkdir()
        docker_config = docker_dir / "config.json"
        docker_config.write_text('{"auths": {}}')
        monkeypatch.setenv("DOCKER_CONFIG", str(docker_dir))

        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)

        downloader = OrasPyDownloader()
        configs = downloader._get_auth_configs()
        assert len(configs) >= 2
        assert str(reg_auth) in configs
        assert str(docker_config) in configs

    @patch("productmd.oci.oras.client.OrasClient")
    def test_xdg_config_home(self, mock_client_cls, tmp_path, monkeypatch):
        """Test that $XDG_CONFIG_HOME/containers/auth.json is discovered."""
        from productmd.oci import OrasPyDownloader

        mock_client_cls.return_value = MagicMock()
        xdg_dir = tmp_path / "xdg-config"
        containers_dir = xdg_dir / "containers"
        containers_dir.mkdir(parents=True)
        auth_file = containers_dir / "auth.json"
        auth_file.write_text('{"auths": {}}')
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_dir))
        monkeypatch.delenv("REGISTRY_AUTH_FILE", raising=False)
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        monkeypatch.delenv("DOCKER_CONFIG", raising=False)

        downloader = OrasPyDownloader()
        configs = downloader._get_auth_configs()
        assert str(auth_file) in configs

    @patch("productmd.oci.oras.client.OrasClient")
    def test_nonexistent_env_path_ignored(self, mock_client_cls, tmp_path, monkeypatch):
        """Test that non-existent paths from env vars are ignored."""
        from productmd.oci import OrasPyDownloader

        mock_client_cls.return_value = MagicMock()
        monkeypatch.setenv("REGISTRY_AUTH_FILE", "/nonexistent/path/auth.json")
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        monkeypatch.delenv("DOCKER_CONFIG", raising=False)

        downloader = OrasPyDownloader()
        configs = downloader._get_auth_configs()
        assert "/nonexistent/path/auth.json" not in configs


# ---------------------------------------------------------------------------
# Tests: auth loading in download/extract paths
# ---------------------------------------------------------------------------


class TestAuthLoading:
    """Tests that download and extract_contents load auth configs."""

    @patch("productmd.oci.oras.client.OrasClient")
    def test_download_loads_auth(self, mock_client_cls, tmp_path):
        """Test that download() calls auth.load_configs before pulling."""
        from productmd.oci import OrasPyDownloader

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        downloader = OrasPyDownloader()
        dest = str(tmp_path / "output")
        downloader.download("oci://quay.io/fedora/rpms:tag@sha256:" + "a" * 64, dest)

        # auth.load_configs should have been called
        mock_client.auth.load_configs.assert_called_once()

    @patch("productmd.oci.oras.client.OrasClient")
    @patch("productmd.oci.oras.provider.Registry")
    def test_extract_contents_loads_auth(self, mock_registry_cls, mock_client_cls, tmp_path):
        """Test that extract_contents() calls auth.load_configs."""
        from productmd.location import FileEntry
        from productmd.oci import OrasPyDownloader

        mock_client_cls.return_value = MagicMock()
        mock_registry = MagicMock()
        mock_registry_cls.return_value = mock_registry

        def write_blob(container, digest, outfile):
            os.makedirs(os.path.dirname(outfile) or ".", exist_ok=True)
            with open(outfile, "wb") as f:
                f.write(b"content")

        mock_registry.download_blob.side_effect = write_blob

        contents = [
            FileEntry(file="file.txt", size=7, checksum=None, layer_digest="sha256:" + "a" * 64),
        ]

        dest_dir = str(tmp_path / "extracted")
        downloader = OrasPyDownloader()
        downloader.extract_contents("oci://registry/repo@sha256:" + "b" * 64, contents, dest_dir)

        mock_registry.auth.load_configs.assert_called_once()
