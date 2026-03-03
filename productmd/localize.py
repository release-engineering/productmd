"""
Localization tool for productmd v2.0 distributed composes.

Downloads a distributed v2.0 compose to local storage, recreating the
v1.2 filesystem layout.  Supports HTTPS/HTTP and OCI registry downloads
with parallel execution, checksum verification, and configurable error
handling.

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
import os
import time
import urllib.request
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional, Tuple
from urllib.error import HTTPError, URLError

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


#: Default chunk size for streaming downloads (8 KB)
_CHUNK_SIZE = 8192


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
) -> None:
    """
    Download a file from an HTTP(S) URL to a local path.

    Downloads to a temporary file (``dest_path + ".tmp"``) then renames
    atomically to avoid partial files.  Retries on failure with
    exponential backoff.

    :param url: HTTP(S) URL to download from
    :param dest_path: Local file path to save to
    :param retries: Number of retry attempts (default: 3)
    :param progress_callback: Optional callback for progress events
    :param filename: Relative path for progress event reporting
    :raises urllib.error.URLError: If all retry attempts fail
    """
    parent_dir = os.path.dirname(dest_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    tmp_path = dest_path + ".tmp"
    last_error = None

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=_get_default_headers())
            response = urllib.request.urlopen(req)
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
            logger.warning(f"Download attempt {attempt + 1}/{retries + 1} failed for {url}: {e}")
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
    logger.warning(f"No checksum available for {dest_path}, skipping based on file existence")
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
) -> Tuple[List[HttpTask], List[OciTask]]:
    """
    Collect all remote artifacts that need downloading.

    :return: Tuple of (http_tasks, oci_tasks) where http_tasks is a list
        of :class:`HttpTask` namedtuples and oci_tasks is a list of
        :class:`OciTask` namedtuples
    """
    compose_root = os.path.join(output_dir, "compose")
    http_tasks = []
    oci_tasks = []

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
        # Variant paths are directory references, not downloadable files
        if entry.metadata_type == "variant_path":
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

    return http_tasks, oci_tasks


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
            logger.info(f"Skipping existing OCI artifact: {task.rel_path}")
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
                logger.error(f"Failed to download OCI artifact {task.rel_path}: {e}")
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
                    logger.error(f"Failed to download OCI artifact {task.rel_path}: {e}")
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
) -> LocalizeResult:
    """
    Localize a distributed v2.0 compose to local storage.

    Downloads all remote artifacts referenced by Location objects in the
    provided metadata, recreating the standard v1.2 filesystem layout.
    After downloading, writes v1.2 metadata files to the output directory.

    Supports both HTTPS/HTTP and OCI registry downloads.  OCI downloads
    require ``oras-py`` (``pip install productmd[oci]``).  Authentication
    supports Docker and Podman credential stores.

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
    :return: :class:`LocalizeResult` with download statistics
    :raises RuntimeError: If OCI URLs are present but oras-py is not installed
    :raises urllib.error.URLError: If a download fails and fail_fast is True
    """
    # Collect all remote download tasks
    http_tasks, oci_tasks = _collect_download_tasks(
        output_dir,
        images,
        rpms,
        extra_files,
        modules,
        composeinfo,
    )
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
            logger.info(f"Skipping existing file: {task.rel_path}")
            continue
        download_tasks.append(task)

    if not download_tasks:
        logger.info("No HTTP files to download")
    elif parallel_downloads <= 1:
        # Sequential downloads
        for task in download_tasks:
            try:
                _download_https(task.url, task.dest_path, retries, progress_callback, task.rel_path)
                # Verify checksum after download
                if verify_checksums and task.location is not None and task.location.checksum is not None:
                    if not task.location.verify(task.dest_path):
                        raise ValueError(f"Checksum verification failed for {task.rel_path}")
                downloaded += 1
            except Exception as e:
                failed += 1
                errors.append((task.rel_path, e))
                _emit(progress_callback, "error", task.rel_path, error=e)
                logger.error(f"Failed to download {task.rel_path}: {e}")
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
                    logger.error(f"Failed to download {task.rel_path}: {e}")
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
    logger.info(f"Localization complete: {result.downloaded} downloaded, {result.skipped} skipped, {result.failed} failed")
    return result
