"""
Localization tool for productmd v2.0 distributed composes.

Downloads a distributed v2.0 compose to local storage, recreating the
v1.2 filesystem layout.  Supports HTTPS/HTTP and OCI registry downloads
with parallel execution, checksum verification, and configurable error
handling.

HTTP downloads support authentication via ``~/.netrc`` (or a custom
netrc file).  Credentials matching the download URL hostname are sent
as HTTP Basic authentication headers.

OCI registry downloads require the ``oras-py`` package
(``pip install productmd[oci]``).  Authentication supports both Docker
and Podman credential stores (``docker login`` / ``podman login``).

Example::

    from productmd.compose import Compose
    from productmd.localize import localize_compose

    compose = Compose("https://cdn.example.com/compose/")
    result = localize_compose(
        output_dir="/mnt/local-compose",
        images=compose.images,
        rpms=compose.rpms,
        composeinfo=compose.info,
        parallel_downloads=8,
        verify_checksums=True,
        skip_existing=True,
    )
    print(f"Downloaded {result.downloaded}, skipped {result.skipped}, failed {result.failed}")
"""

import logging
import netrc
import os
import time
import urllib.request
from base64 import b64encode
import defusedxml.ElementTree as ET
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse, urljoin

from productmd.common import _get_default_headers
from productmd.convert import downgrade_to_v1, iter_all_locations


__all__ = (
    "DownloadEvent",
    "LocalizeResult",
    "localize_compose",
)


logger = logging.getLogger(__name__)


DownloadEvent = namedtuple(
    "DownloadEvent",
    [
        "event_type",
        "filename",
        "bytes_downloaded",
        "total_bytes",
        "error",
    ],
)
"""
Progress event emitted during downloads.

:param event_type: One of ``"start"``, ``"progress"``, ``"complete"``,
    ``"error"``, ``"skip"``
:param filename: Relative path of the artifact being downloaded
:param bytes_downloaded: Bytes downloaded so far (0 for ``"start"``)
:param total_bytes: Total file size from Content-Length, or ``None`` if unknown
:param error: Exception object for ``"error"`` events, ``None`` otherwise
"""


LocalizeResult = namedtuple(
    "LocalizeResult",
    [
        "downloaded",
        "skipped",
        "failed",
        "errors",
    ],
)
"""
Result of a localization operation.

:param downloaded: Number of files successfully downloaded
:param skipped: Number of files skipped (already exist with valid checksum)
:param failed: Number of files that failed to download
:param errors: List of ``(path, exception)`` tuples for failed downloads
"""


def _get_netrc_auth_header(
    url: str,
    netrc_file: Optional[str] = None,
) -> Optional[str]:
    """
    Look up HTTP Basic auth credentials from a netrc file.

    Searches the netrc file for credentials matching the hostname in
    *url*.  If found, returns a ``Basic`` Authorization header value.

    :param url: URL whose hostname is used for the netrc lookup
    :param netrc_file: Path to a netrc file.  When ``None``, the
        standard ``~/.netrc`` (or ``~/_netrc`` on Windows) is used.
    :return: ``"Basic <base64>"`` string, or ``None`` if no credentials
        are found or the netrc file is missing / malformed
    """
    try:
        rc = netrc.netrc(netrc_file)
        host = urlparse(url).hostname
        if not host:
            return None
        auth = rc.authenticators(host)
        if auth:
            login, _, password = auth
            credentials = b64encode(f"{login}:{password}".encode()).decode()
            return f"Basic {credentials}"
    except (FileNotFoundError, netrc.NetrcParseError, OSError) as e:
        logger.debug("netrc lookup failed: %s", e)
    return None


def _validate_credential(value: str, name: str) -> str:
    """Reject credential values containing CR or LF to prevent header injection.

    :param value: The credential value to validate
    :param name: Human-readable name for error messages (e.g., "token")
    :return: The value unchanged if valid
    :raises ValueError: If the value contains CR or LF characters
    """
    if "\r" in value or "\n" in value:
        raise ValueError(f"{name} contains illegal newline characters")
    return value


def _build_auth_header(
    url: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    token: Optional[str] = None,
    netrc_file: Optional[str] = None,
) -> Optional[str]:
    """
    Resolve an HTTP Authorization header value.

    Determines the appropriate authorization header using the following
    precedence (highest first):

    1. Bearer token (``token``)
    2. Explicit Basic credentials (``username`` + ``password``)
    3. Netrc lookup by URL hostname

    :param url: URL whose hostname is used for netrc lookup
    :param username: Username for HTTP Basic authentication
    :param password: Password for HTTP Basic authentication
    :param token: Bearer token for HTTP authentication
    :param netrc_file: Path to a netrc file (default: ``~/.netrc``)
    :return: Authorization header value, or ``None`` if no credentials
        are available
    :raises ValueError: If any credential contains CR or LF characters
    """
    if token is not None:
        _validate_credential(token, "token")
        return f"Bearer {token}"
    if username is not None and password is not None:
        _validate_credential(username, "username")
        _validate_credential(password, "password")
        credentials = b64encode(f"{username}:{password}".encode()).decode()
        return f"Basic {credentials}"
    return _get_netrc_auth_header(url, netrc_file)


def _effective_port(parsed):
    """Return the effective port for a parsed URL.

    Resolves ``None`` (no explicit port) to the default port for the
    scheme: 443 for HTTPS, 80 for HTTP.  This prevents false mismatches
    when comparing ``https://host/path`` (port=None) with
    ``https://host:443/path`` (port=443).
    """
    if parsed.port is not None:
        return parsed.port
    return 443 if parsed.scheme == "https" else 80


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Redirect handler that strips Authorization on cross-origin redirects.

    Prevents credential leakage when a server (e.g. Pulp) redirects to
    a different origin (e.g. CDN or S3 presigned URL).  Matches curl's
    default behavior of comparing scheme + host + port.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None:
            original = urlparse(req.full_url)
            redirect = urlparse(new_req.full_url)
            original_origin = (original.scheme, original.hostname, _effective_port(original))
            redirect_origin = (redirect.scheme, redirect.hostname, _effective_port(redirect))
            if original_origin != redirect_origin:
                new_req.remove_header("Authorization")
                logger.debug(
                    "Stripped Authorization header on redirect from %s to %s",
                    req.full_url,
                    newurl,
                )
        return new_req


_opener = urllib.request.build_opener(_SafeRedirectHandler)

#: Default chunk size for streaming downloads (8 KB)
_CHUNK_SIZE = 8192

#: Variant path fields that are YUM repository roots containing repodata/
_REPO_FIELDS = frozenset({"repository", "debug_repository", "source_repository"})

#: XML namespace used in repomd.xml
_REPOMD_NS = "http://linux.duke.edu/metadata/repo"


def _parse_repomd_xml(xml_bytes: bytes) -> List[dict]:
    """
    Parse a ``repomd.xml`` and return metadata about each referenced file.

    :param xml_bytes: Raw XML content of ``repomd.xml``
    :return: List of dicts with keys ``href``, ``checksum``, ``checksum_type``, ``size``
    """
    root = ET.fromstring(xml_bytes)
    entries = []
    for data_elem in root.findall(f"{{{_REPOMD_NS}}}data"):
        location = data_elem.find(f"{{{_REPOMD_NS}}}location")
        if location is None:
            continue
        href = location.get("href")
        if not href:
            continue

        entry = {"href": href}

        checksum_elem = data_elem.find(f"{{{_REPOMD_NS}}}checksum")
        if checksum_elem is not None and checksum_elem.text:
            entry["checksum_type"] = checksum_elem.get("type", "sha256")
            entry["checksum"] = checksum_elem.text

        size_elem = data_elem.find(f"{{{_REPOMD_NS}}}size")
        if size_elem is not None and size_elem.text:
            entry["size"] = int(size_elem.text)

        entries.append(entry)
    return entries


def _discover_repodata_tasks(
    repo_entries: List[Tuple[str, str]],
    compose_root: str,
    retries: int = 3,
    netrc_file: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    token: Optional[str] = None,
) -> List:
    """
    Fetch ``repomd.xml`` for each repository and generate download tasks.

    For each repository variant path, downloads ``repodata/repomd.xml``,
    parses it to discover referenced files, and creates :class:`HttpTask`
    entries for ``repomd.xml`` itself and each referenced file.

    Deduplicates repositories by URL to avoid fetching the same
    ``repomd.xml`` multiple times (e.g., source repos shared across arches).

    :param repo_entries: List of ``(url, local_path)`` tuples for each
        repository root
    :param compose_root: Local compose root directory
    :param retries: Number of retry attempts for fetching ``repomd.xml``
    :return: List of :class:`HttpTask` for all repodata files
    """
    tasks = []
    seen_urls = set()

    for repo_url, repo_local_path in repo_entries:
        if repo_url in seen_urls:
            continue
        seen_urls.add(repo_url)

        # Ensure trailing slash for proper URL joining
        if not repo_url.endswith("/"):
            repo_url += "/"

        repomd_url = urljoin(repo_url, "repodata/repomd.xml")
        repomd_local = os.path.join(repo_local_path, "repodata", "repomd.xml")
        repomd_dest = os.path.join(compose_root, repomd_local)

        # Fetch repomd.xml
        logger.info("Fetching repomd.xml from %s", repomd_url)
        last_error = None
        xml_bytes = None

        headers = _get_default_headers()
        auth_header = _build_auth_header(repomd_url, username, password, token, netrc_file)
        if auth_header:
            headers["Authorization"] = auth_header

        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(repomd_url, headers=headers)
                response = _opener.open(req)
                xml_bytes = response.read()
                break
            except (HTTPError, URLError, OSError) as e:
                last_error = e
                logger.warning(
                    "Fetch attempt %d/%d failed for %s: %s",
                    attempt + 1,
                    retries + 1,
                    repomd_url,
                    e,
                )
                if isinstance(e, HTTPError) and e.code in (401, 403):
                    break
                if attempt < retries:
                    time.sleep(2**attempt)

        if xml_bytes is None:
            logger.error("Failed to fetch repomd.xml from %s: %s", repomd_url, last_error)
            continue

        # Save repomd.xml itself
        os.makedirs(os.path.dirname(repomd_dest), exist_ok=True)
        with open(repomd_dest, "wb") as f:
            f.write(xml_bytes)

        # Parse and generate tasks for referenced files
        try:
            repodata_entries = _parse_repomd_xml(xml_bytes)
        except ET.ParseError as e:
            logger.error("Failed to parse repomd.xml from %s: %s", repomd_url, e)
            continue

        for entry in repodata_entries:
            href = entry["href"]

            # Guard against path traversal in href values
            normalized = os.path.normpath(href)
            if normalized.startswith(("..", "/")) or "\\" in href:
                logger.warning("Skipping suspicious repodata href: %s", href)
                continue

            file_url = urljoin(repo_url, href)
            file_local = os.path.join(repo_local_path, href)
            file_dest = os.path.join(compose_root, file_local)

            tasks.append(
                HttpTask(
                    url=file_url,
                    dest_path=file_dest,
                    location=None,
                    rel_path=file_local,
                )
            )

    return tasks


def _emit(
    callback: Optional[Callable],
    event_type: str,
    filename: str,
    bytes_downloaded: int = 0,
    total_bytes: Optional[int] = None,
    error: Optional[Exception] = None,
) -> None:
    """Emit a DownloadEvent to the progress callback if provided."""
    if callback is not None:
        callback(DownloadEvent(event_type, filename, bytes_downloaded, total_bytes, error))


def _download_https(
    url: str,
    dest_path: str,
    retries: int = 3,
    progress_callback: Optional[Callable] = None,
    filename: str = "",
    netrc_file: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    token: Optional[str] = None,
) -> None:
    """
    Download a file from an HTTP(S) URL to a local path.

    Downloads to a temporary file (``dest_path + ".tmp"``) then renames
    atomically to avoid partial files.  Retries on failure with
    exponential backoff.

    Authentication is resolved via :func:`_build_auth_header` with the
    following precedence: Bearer *token* > explicit *username*/*password*
    (Basic) > netrc lookup.  Authorization headers are automatically
    stripped on cross-origin redirects to prevent credential leakage.

    :param url: HTTP(S) URL to download from
    :param dest_path: Local file path to save to
    :param retries: Number of retry attempts (default: 3)
    :param progress_callback: Optional callback for progress events
    :param filename: Relative path for progress event reporting
    :param netrc_file: Path to a netrc file for credential lookup.
        When ``None``, the standard ``~/.netrc`` is used.
    :param username: Username for HTTP Basic authentication.
    :param password: Password for HTTP Basic authentication.
    :param token: Bearer token for HTTP authentication.
        Takes precedence over Basic credentials and netrc.
    :raises urllib.error.URLError: If all retry attempts fail
    """
    parent_dir = os.path.dirname(dest_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    tmp_path = dest_path + ".tmp"
    last_error = None

    headers = _get_default_headers()
    auth_header = _build_auth_header(url, username, password, token, netrc_file)
    if auth_header:
        headers["Authorization"] = auth_header

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            response = _opener.open(req)
            content_length = response.headers.get("Content-Length")
            total = int(content_length) if content_length else None

            _emit(progress_callback, "start", filename, 0, total)

            downloaded = 0
            with open(tmp_path, "wb") as f:
                while True:
                    chunk = response.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    _emit(progress_callback, "progress", filename, downloaded, total)

            # Atomic rename
            os.rename(tmp_path, dest_path)

            _emit(progress_callback, "complete", filename, downloaded, total)
            return

        except (HTTPError, URLError, OSError) as e:
            last_error = e
            logger.warning("Download attempt %d/%d failed for %s: %s", attempt + 1, retries + 1, url, e)
            # Auth errors won't be fixed by retrying
            if isinstance(e, HTTPError) and e.code in (401, 403):
                raise
            # Clean up partial temp file
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            if attempt < retries:
                # Exponential backoff: 1s, 2s, 4s, ...
                time.sleep(2**attempt)

    raise last_error


def _should_skip(
    dest_path: str,
    location: object,
    verify_checksums: bool,
) -> bool:
    """
    Check whether a file should be skipped.

    :param dest_path: Local file path
    :param location: Location object with checksum/size info
    :param verify_checksums: Whether to verify checksum (not just existence)
    :return: True if the file should be skipped
    """
    if not os.path.isfile(dest_path):
        return False

    if not verify_checksums:
        # Just check existence
        return True

    # Verify checksum if available
    if location is not None and location.checksum is not None:
        try:
            return location.verify(dest_path)
        except (OSError, ValueError):
            return False

    # No checksum to verify — fall back to existence check
    logger.warning("No checksum available for %s, skipping based on file existence", dest_path)
    return True


HttpTask = namedtuple(
    "HttpTask",
    [
        "url",
        "dest_path",
        "location",
        "rel_path",
    ],
)
"""
An HTTP/HTTPS download task.

:param url: Remote URL to download from
:param dest_path: Local file path to save to
:param location: :class:`~productmd.location.Location` object
:param rel_path: Relative path for progress reporting
"""


OciTask = namedtuple(
    "OciTask",
    [
        "oci_url",
        "dest_dir",
        "contents",
        "location",
        "rel_path",
    ],
)
"""
An OCI download task.

:param oci_url: OCI reference URL
:param dest_dir: Local directory to write extracted files
:param contents: List of :class:`~productmd.location.FileEntry` (may be empty)
:param location: :class:`~productmd.location.Location` object
:param rel_path: Relative path for progress reporting
"""


def _collect_download_tasks(
    output_dir: str,
    images: Optional[object] = None,
    rpms: Optional[object] = None,
    extra_files: Optional[object] = None,
    modules: Optional[object] = None,
    composeinfo: Optional[object] = None,
) -> Tuple[List[HttpTask], List[OciTask], List[Tuple[str, str]]]:
    """
    Collect all remote artifacts that need downloading.

    :return: Tuple of (http_tasks, oci_tasks, repo_entries) where
        http_tasks is a list of :class:`HttpTask` namedtuples,
        oci_tasks is a list of :class:`OciTask` namedtuples, and
        repo_entries is a list of ``(url, local_path)`` tuples for
        YUM repository roots whose repodata needs downloading.
    """
    compose_root = os.path.join(output_dir, "compose")
    http_tasks = []
    oci_tasks = []
    repo_entries = []

    for entry in iter_all_locations(
        images=images,
        rpms=rpms,
        extra_files=extra_files,
        modules=modules,
        composeinfo=composeinfo,
    ):
        if entry.location is None:
            continue
        if not entry.location.is_remote:
            continue
        # Variant paths: repository fields need repodata downloading,
        # all other fields are directory references (not downloadable).
        if entry.metadata_type == "variant_path":
            if entry.field_name in _REPO_FIELDS:
                repo_entries.append((entry.location.url, entry.location.local_path))
            continue

        if entry.location.is_oci:
            # oras pull writes files using the original filename from
            # the artifact's title annotation relative to dest_dir.
            # For simple OCI (no contents), dest_dir is the compose
            # root so oras recreates the local_path structure inside it.
            # For OCI with contents, dest_dir is the parent directory
            # where extracted files are placed.
            if entry.location.contents:
                dest_dir = os.path.join(compose_root, entry.location.local_path)
            else:
                dest_dir = compose_root
            oci_tasks.append(
                OciTask(
                    oci_url=entry.location.url,
                    dest_dir=dest_dir,
                    contents=entry.location.contents,
                    location=entry.location,
                    rel_path=entry.path,
                )
            )
        else:
            dest_path = os.path.join(compose_root, entry.location.local_path)
            http_tasks.append(
                HttpTask(
                    url=entry.location.url,
                    dest_path=dest_path,
                    location=entry.location,
                    rel_path=entry.path,
                )
            )

    return http_tasks, oci_tasks, repo_entries


def _deduplicate_http_tasks(
    tasks: List[HttpTask],
) -> List[HttpTask]:
    """
    Remove duplicate HTTP download tasks (same dest_path).

    Raises :class:`ValueError` if two tasks target the same destination
    path but reference different URLs, since one download would silently
    overwrite the other.

    :param tasks: List of HTTP tasks
    :return: Deduplicated list of HTTP tasks
    :raises ValueError: If conflicting URLs map to the same dest_path
    """
    seen = {}
    unique = []
    for task in tasks:
        if task.dest_path in seen:
            if seen[task.dest_path] != task.url:
                raise ValueError(f"Conflicting URLs for {task.dest_path}: {seen[task.dest_path]} vs {task.url}")
            continue
        seen[task.dest_path] = task.url
        unique.append(task)
    return unique


def _deduplicate_oci_tasks(
    tasks: List[OciTask],
) -> List[OciTask]:
    """
    Deduplicate OCI tasks by URL.

    Multiple metadata entries may reference the same OCI image (same URL).
    We keep only the first task per URL since the same image contents
    will be extracted to the same destination.

    :param tasks: List of OCI tasks
    :return: Deduplicated list of OCI tasks
    """
    seen = set()
    unique = []
    for task in tasks:
        if task.oci_url not in seen:
            seen.add(task.oci_url)
            unique.append(task)
    return unique


def _should_skip_oci(
    task: OciTask,
    verify_checksums: bool,
) -> bool:
    """
    Check whether an OCI download should be skipped.

    For OCI images with contents, checks that **all** individual files
    exist (and optionally verifies their checksums).  For simple OCI
    downloads (no contents), checks the single output file.

    :param task: OCI download task
    :param verify_checksums: Whether to verify checksums
    :return: True if the download should be skipped
    """
    # An empty list is treated the same as None (simple OCI download).
    if task.contents:
        from productmd.location import compute_checksum, parse_checksum

        # All files must exist for skip
        for file_entry in task.contents:
            file_path = os.path.join(task.dest_dir, file_entry.file)
            if not os.path.isfile(file_path):
                return False
            if verify_checksums and file_entry.checksum:
                try:
                    algorithm, _ = parse_checksum(file_entry.checksum)
                    actual = compute_checksum(file_path, algorithm)
                    if actual != file_entry.checksum:
                        return False
                except (OSError, ValueError):
                    return False
        return True
    else:
        # Simple OCI: dest_dir is the compose root; oras writes to
        # dest_dir/local_path using the artifact's title annotation.
        file_path = os.path.join(task.dest_dir, task.location.local_path)
        return _should_skip(file_path, task.location, verify_checksums)


# ---------------------------------------------------------------------------
# Thread-safety for parallel OCI downloads
#
# oras-py's OrasClient and Registry each hold a requests.Session, which
# is NOT thread-safe (see requests docs).  Sharing a single downloader
# across threads would cause corrupted state (cookies, auth tokens,
# connection pool).
#
# To enable safe parallel downloads we create a **fresh OrasPyDownloader
# (and therefore a fresh OrasClient / requests.Session) per task** inside
# _download_single_oci.  This gives each thread its own isolated network
# stack with no shared mutable state.
#
# What is thread-safe:
#   - get_downloader() — stateless factory, creates a new instance
#   - OrasPyDownloader._get_auth_configs() — static, reads env vars only
#   - _emit() — calls callback(namedtuple); the CLI callback uses
#     print() which is protected by the GIL
#   - os.makedirs(exist_ok=True) — safe for concurrent calls on the
#     same path
#
# What is NOT shared across threads:
#   - OrasClient / requests.Session — one per task
#   - oras.provider.Registry — one per extract_contents() call
#   - Downloaded/failed/skipped counters — tallied by the main thread
#     from future results after join
# ---------------------------------------------------------------------------


def _download_single_oci(
    task: OciTask,
    progress_callback: Optional[Callable],
) -> int:
    """
    Download a single OCI task using a fresh downloader.

    Creates its own :class:`~productmd.oci.OrasPyDownloader` instance
    to ensure thread-safe execution (no shared ``requests.Session``).

    :param task: OCI download task
    :param progress_callback: Optional progress callback
    :return: Number of files downloaded (1 for simple, len(contents)
        for multi-file)
    :raises Exception: Propagated from oras-py on download failure
    """
    from productmd.oci import get_downloader

    # contents may be a non-empty list (multi-file OCI) or None/[]
    # (simple single-artifact OCI).  Both None and [] mean "simple".
    file_count = len(task.contents) if task.contents else 1

    _emit(progress_callback, "start", task.rel_path, 0, task.location.size)

    downloader = get_downloader()
    downloader.download_and_extract(
        oci_url=task.oci_url,
        dest_dir=task.dest_dir,
        contents=task.contents if task.contents else None,
    )

    _emit(progress_callback, "complete", task.rel_path, task.location.size or 0, task.location.size)
    return file_count


def _download_oci_tasks(
    oci_tasks: List[OciTask],
    skip_existing: bool,
    verify_checksums: bool,
    fail_fast: bool,
    parallel_downloads: int,
    progress_callback: Optional[Callable],
) -> Tuple[int, int, int, List[Tuple[str, Exception]]]:
    """
    Download all OCI tasks, optionally in parallel.

    When *parallel_downloads* > 1, tasks are submitted to a
    :class:`~concurrent.futures.ThreadPoolExecutor`.  Each task runs
    with its own :class:`~productmd.oci.OrasPyDownloader` instance
    to avoid sharing ``requests.Session`` across threads (see the
    thread-safety comment block above).

    :param oci_tasks: Deduplicated list of OCI tasks
    :param skip_existing: Skip downloads where all files already exist
    :param verify_checksums: Verify checksums after download
    :param fail_fast: Stop on first failure
    :param parallel_downloads: Max concurrent OCI downloads
    :param progress_callback: Optional progress callback
    :return: Tuple of (downloaded, skipped, failed, errors)
    """
    from productmd.oci import HAS_ORAS

    downloaded = 0
    skipped = 0
    failed = 0
    errors = []

    if not oci_tasks:
        return downloaded, skipped, failed, errors

    if not HAS_ORAS:
        raise RuntimeError("oras-py is required for OCI downloads. Install with: pip install productmd[oci]")

    # Filter tasks based on skip_existing before submitting to executor
    pending_tasks = []
    for task in oci_tasks:
        if skip_existing and _should_skip_oci(task, verify_checksums):
            skipped += 1
            _emit(progress_callback, "skip", task.rel_path)
            logger.info("Skipping existing OCI artifact: %s", task.rel_path)
            continue
        pending_tasks.append(task)

    if not pending_tasks:
        return downloaded, skipped, failed, errors

    if parallel_downloads <= 1:
        # Sequential downloads
        for task in pending_tasks:
            try:
                file_count = _download_single_oci(task, progress_callback)
                downloaded += file_count
            except Exception as e:
                file_count = len(task.contents) if task.contents else 1
                failed += file_count
                errors.append((task.rel_path, e))
                _emit(progress_callback, "error", task.rel_path, error=e)
                logger.error("Failed to download OCI artifact %s: %s", task.rel_path, e)
                if fail_fast:
                    break
    else:
        # Parallel downloads — each task gets its own downloader
        with ThreadPoolExecutor(max_workers=parallel_downloads) as executor:
            future_to_task = {}
            for task in pending_tasks:
                future = executor.submit(
                    _download_single_oci,
                    task,
                    progress_callback,
                )
                future_to_task[future] = task

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    file_count = future.result()
                    downloaded += file_count
                except Exception as e:
                    file_count = len(task.contents) if task.contents else 1
                    failed += file_count
                    errors.append((task.rel_path, e))
                    _emit(progress_callback, "error", task.rel_path, error=e)
                    logger.error("Failed to download OCI artifact %s: %s", task.rel_path, e)
                    if fail_fast:
                        for f in future_to_task:
                            f.cancel()
                        break

    return downloaded, skipped, failed, errors


def localize_compose(
    output_dir: str,
    images: Optional[object] = None,
    rpms: Optional[object] = None,
    extra_files: Optional[object] = None,
    modules: Optional[object] = None,
    composeinfo: Optional[object] = None,
    parallel_downloads: int = 4,
    verify_checksums: bool = True,
    skip_existing: bool = False,
    fail_fast: bool = True,
    retries: int = 3,
    progress_callback: Optional[Callable] = None,
    netrc_file: Optional[str] = None,
    http_username: Optional[str] = None,
    http_password: Optional[str] = None,
    http_token: Optional[str] = None,
) -> LocalizeResult:
    """
    Localize a distributed v2.0 compose to local storage.

    Downloads all remote artifacts referenced by Location objects in the
    provided metadata, recreating the standard v1.2 filesystem layout.
    After downloading, writes v1.2 metadata files to the output directory.

    Supports both HTTPS/HTTP and OCI registry downloads.  OCI downloads
    require ``oras-py`` (``pip install productmd[oci]``).  Authentication
    supports Docker and Podman credential stores.

    HTTP downloads support authentication with the following precedence:
    Bearer token > explicit Basic credentials > netrc lookup.

    :param output_dir: Local directory to create the compose layout
    :param images: :class:`~productmd.images.Images` instance
    :param rpms: :class:`~productmd.rpms.Rpms` instance
    :param extra_files: :class:`~productmd.extra_files.ExtraFiles` instance
    :param modules: :class:`~productmd.modules.Modules` instance
    :param composeinfo: :class:`~productmd.composeinfo.ComposeInfo` instance
    :param parallel_downloads: Number of concurrent download threads (default: 4)
    :param verify_checksums: Verify SHA-256 after download (default: True)
    :param skip_existing: Skip files that already exist with valid checksum (default: False)
    :param fail_fast: Stop on first failure (default: True).
        When False, collects errors and continues.
    :param retries: Number of retry attempts per download (default: 3)
    :param progress_callback: Optional callable receiving
        :class:`DownloadEvent` instances for progress tracking
    :param netrc_file: Path to a netrc file for HTTP credential lookup.
        When ``None``, the standard ``~/.netrc`` is used.
    :param http_username: Username for HTTP Basic authentication.
    :param http_password: Password for HTTP Basic authentication.
    :param http_token: Bearer token for HTTP authentication.
        Takes precedence over Basic credentials and netrc.
        Mutually exclusive with ``http_username``/``http_password``.
    :return: :class:`LocalizeResult` with download statistics
    :raises RuntimeError: If OCI URLs are present but oras-py is not installed
    :raises urllib.error.URLError: If a download fails and fail_fast is True
    :raises ValueError: If auth parameters are invalid (e.g., username
        without password, or token with username/password)
    """
    # Validate auth parameters
    if (http_username is None) != (http_password is None):
        raise ValueError("http_username and http_password must be provided together")
    if http_token and (http_username or http_password):
        raise ValueError("http_token is mutually exclusive with http_username/http_password")

    # Collect all remote download tasks
    http_tasks, oci_tasks, repo_entries = _collect_download_tasks(
        output_dir,
        images,
        rpms,
        extra_files,
        modules,
        composeinfo,
    )

    # --- Phase 0: Repodata discovery ---
    # Fetch repomd.xml for each repository and generate download tasks
    # for the referenced metadata files (primary, filelists, comps, etc.).
    compose_root = os.path.join(output_dir, "compose")
    if repo_entries:
        repodata_tasks = _discover_repodata_tasks(
            repo_entries,
            compose_root,
            retries,
            netrc_file=netrc_file,
            username=http_username,
            password=http_password,
            token=http_token,
        )
        http_tasks.extend(repodata_tasks)
        logger.info("Discovered %d repodata files from %d repositories", len(repodata_tasks), len(repo_entries))

    http_tasks = _deduplicate_http_tasks(http_tasks)
    oci_tasks = _deduplicate_oci_tasks(oci_tasks)

    downloaded = 0
    skipped = 0
    failed = 0
    errors = []

    # --- Phase 1: HTTP/HTTPS downloads ---

    # Filter tasks based on skip_existing
    download_tasks = []
    for task in http_tasks:
        if skip_existing and _should_skip(task.dest_path, task.location, verify_checksums):
            skipped += 1
            _emit(progress_callback, "skip", task.rel_path)
            logger.info("Skipping existing file: %s", task.rel_path)
            continue
        download_tasks.append(task)

    if not download_tasks:
        logger.info("No HTTP files to download")
    elif parallel_downloads <= 1:
        # Sequential downloads
        for task in download_tasks:
            try:
                _download_https(
                    task.url,
                    task.dest_path,
                    retries,
                    progress_callback,
                    task.rel_path,
                    netrc_file,
                    http_username,
                    http_password,
                    http_token,
                )
                # Verify checksum after download
                if verify_checksums and task.location is not None and task.location.checksum is not None:
                    if not task.location.verify(task.dest_path):
                        raise ValueError(f"Checksum verification failed for {task.rel_path}")
                downloaded += 1
            except Exception as e:
                failed += 1
                errors.append((task.rel_path, e))
                _emit(progress_callback, "error", task.rel_path, error=e)
                logger.error("Failed to download %s: %s", task.rel_path, e)
                if fail_fast:
                    break
    else:
        # Parallel downloads
        with ThreadPoolExecutor(max_workers=parallel_downloads) as executor:
            future_to_task = {}
            for task in download_tasks:
                future = executor.submit(
                    _download_https,
                    task.url,
                    task.dest_path,
                    retries,
                    progress_callback,
                    task.rel_path,
                    netrc_file,
                    http_username,
                    http_password,
                    http_token,
                )
                future_to_task[future] = task

            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    future.result()
                    # Verify checksum after download
                    if verify_checksums and task.location is not None and task.location.checksum is not None:
                        if not task.location.verify(task.dest_path):
                            raise ValueError(f"Checksum verification failed for {task.rel_path}")
                    downloaded += 1
                except Exception as e:
                    failed += 1
                    errors.append((task.rel_path, e))
                    _emit(progress_callback, "error", task.rel_path, error=e)
                    logger.error("Failed to download %s: %s", task.rel_path, e)
                    if fail_fast:
                        # Cancel remaining futures
                        for f in future_to_task:
                            f.cancel()
                        break

    # --- Phase 2: OCI registry downloads ---

    if oci_tasks and not (fail_fast and failed > 0):
        oci_downloaded, oci_skipped, oci_failed, oci_errors = _download_oci_tasks(
            oci_tasks,
            skip_existing=skip_existing,
            verify_checksums=verify_checksums,
            fail_fast=fail_fast,
            parallel_downloads=parallel_downloads,
            progress_callback=progress_callback,
        )
        downloaded += oci_downloaded
        skipped += oci_skipped
        failed += oci_failed
        errors.extend(oci_errors)

    # Write v1.2 metadata to compose/metadata/ directory.
    # TODO: .treeinfo generation is planned but deferred — it requires
    # understanding repository structure and is independent of downloading.
    metadata_dir = os.path.join(output_dir, "compose", "metadata")
    downgrade_to_v1(
        output_dir=metadata_dir,
        images=images,
        rpms=rpms,
        extra_files=extra_files,
        modules=modules,
        composeinfo=composeinfo,
    )

    result = LocalizeResult(downloaded, skipped, failed, errors)
    logger.info("Localization complete: %d downloaded, %d skipped, %d failed", result.downloaded, result.skipped, result.failed)
    return result
