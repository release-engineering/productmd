"""
OCI image download and extraction utilities for productmd.

Provides tools for downloading ORAS-compatible OCI artifacts from
registries.  Uses the ``oras-py`` Python SDK as the download backend.

Only ORAS-compatible artifacts (raw file blobs) are supported.
Traditional container image layers (tar.gz) will raise an error —
use ``oras push`` to publish artifacts in the supported format.

All OCI-related utilities are contained in this module to facilitate
future refactoring into a sub-package if complexity grows.

Example::

    from productmd.oci import get_downloader

    downloader = get_downloader()
    downloader.download_and_extract(
        oci_url="oci://quay.io/fedora/server:41-x86_64@sha256:abc...",
        dest_dir="/tmp/extracted",
        contents=image.location.contents,  # list of FileEntry objects
    )

.. note::

    OCI push operations (for supplementary pipeline attachments as
    described in PRODUCTMD-2.0-PLAN.md Sections 14-20) are planned
    but not yet implemented.
"""

import json
import os
import tarfile
import tempfile
from typing import List, Optional

from productmd.location import compute_checksum

try:
    import oras.client
    import oras.provider

    HAS_ORAS = True
except ImportError:
    HAS_ORAS = False


__all__ = (
    "get_downloader",
    "parse_oci_index",
    "parse_oci_manifest",
    "find_layer_blob",
)


class OciDownloader:
    """
    Abstract interface for OCI image download operations.

    Subclasses implement the actual download mechanism.

    .. note::

        Push operations (for supplementary pipeline attachments as
        described in PRODUCTMD-2.0-PLAN.md Sections 14-20) are planned
        but not yet implemented in this interface.
    """

    def download(self, oci_url: str, dest_dir: str) -> None:
        """
        Download OCI artifacts to a local directory.

        :param oci_url: OCI reference URL (``oci://registry/repo@sha256:...``)
        :param dest_dir: Local directory to write downloaded files
        :raises NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError

    def extract_contents(
        self,
        oci_url: str,
        contents: List,
        dest_dir: str,
    ) -> None:
        """
        Download specific layers by digest based on a FileEntry contents list.

        :param oci_url: OCI reference URL
        :param contents: List of :class:`~productmd.location.FileEntry` objects
        :param dest_dir: Directory to write extracted files
        :raises NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError

    def download_and_extract(
        self,
        oci_url: str,
        dest_dir: str,
        contents: Optional[List] = None,
    ) -> None:
        """
        Download an OCI image and extract its contents.

        For single-artifact OCI images (no *contents*), downloads the
        artifact directly.  For multi-file OCI images (with *contents*),
        downloads each file from its corresponding layer by digest.

        :param oci_url: OCI reference URL
        :param dest_dir: Directory to write extracted files
        :param contents: Optional list of :class:`~productmd.location.FileEntry`
        :raises NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError


class OrasPyDownloader(OciDownloader):
    """
    OCI artifact operations via the ``oras-py`` Python SDK.

    Requires the ``oras`` package to be installed
    (``pip install productmd[oci]``).

    Only ORAS-compatible artifacts (raw file blobs pushed via
    ``oras push``) are supported.  Traditional container image layers
    (tar.gz archives) are detected and rejected with a clear error
    message.

    Authentication supports both Docker and Podman credential stores.
    Credentials are discovered from (in order):

    1. ``$REGISTRY_AUTH_FILE`` (Podman/Skopeo)
    2. ``$XDG_RUNTIME_DIR/containers/auth.json`` (Podman runtime)
    3. ``$XDG_CONFIG_HOME/containers/auth.json`` (Podman persistent, defaults to ``~/.config``)
    4. ``$DOCKER_CONFIG/config.json`` (Docker env override)
    5. ``~/.docker/config.json`` (Docker default, oras-py built-in fallback)
    """

    def __init__(self) -> None:
        if not HAS_ORAS:
            raise RuntimeError("oras-py is required for OCI downloads. Install with: pip install productmd[oci]")
        self._client = oras.client.OrasClient()

    @staticmethod
    def _get_auth_configs() -> List[str]:
        """
        Discover container auth config files from Podman and Docker locations.

        oras-py only checks ``~/.docker/config.json`` by default.  This
        method adds Podman credential locations so that ``podman login``
        credentials are found automatically.

        :return: List of existing auth config file paths (may be empty)
        """
        configs = []

        # $REGISTRY_AUTH_FILE — Podman/Skopeo environment variable
        reg_auth = os.environ.get("REGISTRY_AUTH_FILE")
        if reg_auth and os.path.exists(reg_auth):
            configs.append(reg_auth)

        # $XDG_RUNTIME_DIR/containers/auth.json — Podman runtime auth
        xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
        if xdg_runtime:
            p = os.path.join(xdg_runtime, "containers", "auth.json")
            if os.path.exists(p):
                configs.append(p)

        # $XDG_CONFIG_HOME/containers/auth.json — Podman persistent auth
        # Falls back to ~/.config per XDG Base Directory Specification
        xdg_config = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        p = os.path.join(xdg_config, "containers", "auth.json")
        if os.path.exists(p):
            configs.append(p)

        # $DOCKER_CONFIG/config.json — Docker env override
        docker_cfg = os.environ.get("DOCKER_CONFIG")
        if docker_cfg:
            p = os.path.join(docker_cfg, "config.json")
            if os.path.exists(p):
                configs.append(p)

        # ~/.docker/config.json is always appended by oras-py internally,
        # so we don't need to add it here.
        return configs

    def download(self, oci_url: str, dest_dir: str) -> None:
        """
        Download OCI artifacts via ``oras-py`` client.

        Strips the ``oci://`` prefix and calls ``client.pull()`` which
        downloads all artifact layers directly as files.

        :param oci_url: OCI reference URL (``oci://registry/repo@sha256:...``)
        :param dest_dir: Local directory to write downloaded files
        """
        target = oci_url.replace("oci://", "", 1)
        os.makedirs(dest_dir, exist_ok=True)

        # Load Podman/Docker credentials before pulling
        container = self._client.get_container(target)
        auth_configs = self._get_auth_configs()
        self._client.auth.load_configs(container, configs=auth_configs or None)

        self._client.pull(target=target, outdir=dest_dir)

    def extract_contents(
        self,
        oci_url: str,
        contents: List,
        dest_dir: str,
    ) -> None:
        """
        Download specific layers by digest for the contents field.

        For each :class:`~productmd.location.FileEntry` in *contents*,
        downloads the layer blob matching ``layer_digest`` from the
        registry.  Only raw ORAS blobs are supported; tar.gz container
        image layers are rejected with an error.

        :param oci_url: OCI reference URL
        :param contents: List of :class:`~productmd.location.FileEntry`
        :param dest_dir: Directory to write extracted files
        :raises ValueError: If a layer is a tar archive or checksum doesn't match
        :raises RuntimeError: If oras-py is not installed
        """
        target = oci_url.replace("oci://", "", 1)
        registry = oras.provider.Registry()
        container = registry.get_container(target)

        # Load Podman/Docker credentials for blob downloads
        auth_configs = self._get_auth_configs()
        registry.auth.load_configs(container, configs=auth_configs or None)

        for file_entry in contents:
            dest_path = os.path.join(dest_dir, file_entry.file)
            parent = os.path.dirname(dest_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            # Download blob to temp file for validation before final placement
            with tempfile.NamedTemporaryFile(delete=False, dir=parent or ".") as tmp:
                tmp_path = tmp.name

            try:
                registry.download_blob(container, file_entry.layer_digest, tmp_path)

                # Reject tar.gz container image layers — only ORAS raw blobs supported
                if tarfile.is_tarfile(tmp_path):
                    raise ValueError(
                        f"Layer {file_entry.layer_digest} for '{file_entry.file}' "
                        f"is a tar archive (container image layer). Only "
                        f"ORAS-compatible raw file blobs are supported. "
                        f"Re-push the artifact using 'oras push' instead of "
                        f"container image tools."
                    )

                # Move to final destination
                os.rename(tmp_path, dest_path)
                tmp_path = None  # prevent cleanup

            finally:
                if tmp_path is not None and os.path.exists(tmp_path):
                    os.unlink(tmp_path)

            # Verify checksum if available
            if file_entry.checksum:
                actual = compute_checksum(dest_path, "sha256")
                if actual != file_entry.checksum:
                    raise ValueError(f"Checksum mismatch for {file_entry.file}: expected {file_entry.checksum}, got {actual}")

    def download_and_extract(
        self,
        oci_url: str,
        dest_dir: str,
        contents: Optional[List] = None,
    ) -> None:
        """
        Download an OCI image and extract its contents to *dest_dir*.

        For single-artifact OCI images (no *contents*), uses
        ``client.pull()`` to download files directly.  For multi-file
        OCI images (with *contents*), downloads each layer by digest
        via the registry provider API.

        :param oci_url: OCI reference URL
        :param dest_dir: Directory to write extracted files
        :param contents: Optional list of :class:`~productmd.location.FileEntry`
        """
        if contents:
            self.extract_contents(oci_url, contents, dest_dir)
        else:
            self.download(oci_url, dest_dir)


# ---------------------------------------------------------------------------
# OCI layout parsing utilities (pure stdlib)
#
# These functions operate on local OCI layout directories and do not
# require oras-py.  They are useful for inspecting OCI images that
# have already been downloaded to disk.
# ---------------------------------------------------------------------------


def parse_oci_index(image_dir: str) -> List[dict]:
    """
    Parse ``index.json`` from an OCI layout directory.

    :param image_dir: Path to OCI layout directory
    :return: List of manifest descriptors (dicts with ``digest``,
        ``mediaType``, ``size``)
    :raises FileNotFoundError: If ``index.json`` is missing
    """
    index_path = os.path.join(image_dir, "index.json")
    with open(index_path) as f:
        index = json.load(f)
    return index.get("manifests", [])


def parse_oci_manifest(image_dir: str, manifest_digest: str) -> dict:
    """
    Parse a manifest blob from an OCI layout directory.

    :param image_dir: Path to OCI layout directory
    :param manifest_digest: Digest string (e.g., ``"sha256:abc..."``)
    :return: Manifest dict with ``config`` and ``layers`` keys
    :raises FileNotFoundError: If the manifest blob is missing
    """
    algo, digest = manifest_digest.split(":", 1)
    blob_path = os.path.join(image_dir, "blobs", algo, digest)
    with open(blob_path) as f:
        return json.load(f)


def find_layer_blob(image_dir: str, layer_digest: str) -> str:
    """
    Find the blob file path for a given layer digest.

    :param image_dir: Path to OCI layout directory
    :param layer_digest: Digest string (e.g., ``"sha256:def..."``)
    :return: Absolute path to the blob file
    :raises ValueError: If the layer blob is not found
    """
    algo, digest = layer_digest.split(":", 1)
    blob_path = os.path.join(image_dir, "blobs", algo, digest)
    if not os.path.isfile(blob_path):
        raise ValueError(f"Layer blob not found: {layer_digest}")
    return blob_path


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_downloader() -> OciDownloader:
    """
    Get the default OCI downloader.

    Returns an :class:`OrasPyDownloader` instance backed by the
    ``oras-py`` Python SDK.

    :return: An OCI downloader instance
    :raises RuntimeError: If oras-py is not installed
    """
    return OrasPyDownloader()
