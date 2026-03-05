"""
Progress display utilities for productmd CLI tools.

Provides ASCII progress bars for sequential downloads and completion
status lines for parallel downloads.  No external dependencies — uses
only ``sys.stdout`` for output.

Sequential mode shows a per-file progress bar that updates in place
via ``\\r``.  Parallel mode prints a one-line status message as each
file completes.
"""

import os
import sys
import time
from typing import Callable, Optional, Tuple

_DESC_WIDTH = 50


def _should_show_progress_bar() -> bool:
    """
    Return True if interactive progress bars should be shown.

    Progress bars use ``\\r`` carriage returns for in-place updates,
    which creates messy output when redirected to a file or pipe.
    They are disabled when:

    - The ``CI`` environment variable is set (GitHub Actions, GitLab CI,
      Jenkins, and most CI systems set this).
    - ``sys.stdout`` is not a TTY (output redirected to a file or pipe).

    Per-artifact log lines (checksums, OK/FAIL/SKIP) are always printed
    regardless of this check.

    :return: True if progress bars should be displayed
    :rtype: bool
    """
    if os.environ.get("CI"):
        return False
    return sys.stdout.isatty()


def _format_filename(path: str, max_width: int = _DESC_WIDTH) -> str:
    """
    Truncate a file path to fit within *max_width* characters.

    Short paths are right-padded with spaces.  Long paths have
    their middle directory components replaced with ``...``,
    cutting at ``/`` boundaries to preserve readability.  The
    beginning (variant/arch) and end (filename) of the path
    are always preserved.

    :param path: File path to format
    :type path: str
    :param max_width: Maximum width in characters (default: 50)
    :type max_width: int
    :return: Formatted path string, exactly *max_width* characters
    :rtype: str
    """
    if len(path) <= max_width:
        return path.ljust(max_width)

    parts = path.split("/")
    basename = parts[-1]

    # If basename alone is too long, truncate it with leading ...
    if len(basename) >= max_width - 3:
        return ("..." + basename[-(max_width - 3) :]).ljust(max_width)

    # Remove middle components one by one until prefix/.../basename fits
    prefix_parts = parts[:-1]
    while prefix_parts:
        candidate = "/".join(prefix_parts) + "/.../" + basename
        if len(candidate) <= max_width:
            return candidate.ljust(max_width)
        prefix_parts.pop()

    # Nothing fits with a prefix — just show .../basename
    return (".../" + basename).ljust(max_width)


def _format_size(n: Optional[float]) -> str:
    """
    Format a byte count as a human-readable string.

    :param n: Number of bytes
    :type n: Optional[float]
    :return: Formatted string (e.g., ``"512MB"``, ``"2.5GB"``)
    :rtype: str
    """
    if n is None:
        return "?B"
    for unit in ("B", "kB", "MB", "GB", "TB"):
        if abs(n) < 1000:
            if n == int(n):
                return f"{int(n)}{unit}"
            return f"{n:.1f}{unit}"
        n /= 1000.0
    return f"{n:.1f}PB"


def _format_speed(bytes_per_sec: float) -> str:
    """
    Format a download speed as a human-readable string.

    :param bytes_per_sec: Speed in bytes per second
    :type bytes_per_sec: float
    :return: Formatted string (e.g., ``"1.4GB/s"``)
    :rtype: str
    """
    return _format_size(bytes_per_sec) + "/s"


def _print_bar(filename: str, downloaded: int, total: int, speed: float) -> None:
    """
    Print an inline progress bar using ``\\r`` to overwrite the current line.

    :param filename: File path (will be formatted with :func:`_format_filename`)
    :type filename: str
    :param downloaded: Bytes downloaded so far
    :type downloaded: int
    :param total: Total bytes (or 0 if unknown)
    :type total: int
    :param speed: Download speed in bytes/sec
    :type speed: float
    """
    desc = _format_filename(filename)
    total = total or 0
    pct = int(100 * downloaded / total) if total > 0 else 0
    bar_width = 20
    filled = int(bar_width * downloaded / total) if total > 0 else 0
    bar = "=" * filled + " " * (bar_width - filled)
    dl_str = _format_size(downloaded)
    total_str = _format_size(total)
    speed_str = _format_speed(speed) if speed > 0 else "?B/s"
    sys.stdout.write(f"\r{desc} {pct:3d}% [{bar}] {dl_str}/{total_str} [{speed_str}]")
    sys.stdout.flush()


def make_progress_callback(parallel: int = 1) -> Tuple[Callable, Callable]:
    """
    Create a progress callback for download operations.

    In sequential mode (``parallel=1``), shows a per-file ASCII progress
    bar that updates in place via ``\\r``.  In parallel mode
    (``parallel > 1``), prints a one-line status message as each file
    completes, including file size and download speed.

    :param parallel: Number of parallel downloads (1 = sequential)
    :type parallel: int
    :return: (callback, cleanup) tuple
    :rtype: Tuple[Callable, Callable]
    """
    show_bar = _should_show_progress_bar()
    state = {
        "completed": 0,
        "start_times": {},
    }

    def callback(event):
        if event.event_type == "start":
            state["start_times"][event.filename] = time.time()
            if show_bar and parallel <= 1:
                _print_bar(event.filename, 0, event.total_bytes, 0)

        elif event.event_type == "progress":
            if show_bar and parallel <= 1:
                start = state["start_times"].get(event.filename, time.time())
                elapsed = time.time() - start
                speed = event.bytes_downloaded / elapsed if elapsed > 0 else 0
                _print_bar(
                    event.filename,
                    event.bytes_downloaded,
                    event.total_bytes,
                    speed,
                )

        elif event.event_type == "complete":
            state["completed"] += 1
            total = event.total_bytes or 0
            start = state["start_times"].pop(event.filename, time.time())
            elapsed = time.time() - start
            speed = total / elapsed if elapsed > 0 else 0

            if parallel <= 1:
                if show_bar:
                    # Sequential: finish the bar at 100% and move to next line
                    _print_bar(event.filename, total, total, speed)
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                else:
                    # Non-TTY/CI: print completion line without bar
                    print(
                        f"  {_format_filename(event.filename)} done  {_format_size(total)}  {_format_speed(speed)}",
                        flush=True,
                    )
            else:
                # Parallel: always print completion line
                print(
                    f"  {_format_filename(event.filename)} done  {_format_size(total)}  {_format_speed(speed)}",
                    flush=True,
                )

        elif event.event_type == "skip":
            if show_bar and parallel <= 1:
                # Clear any in-progress bar before printing
                try:
                    cols = os.get_terminal_size().columns
                except (AttributeError, ValueError, OSError):
                    cols = 120
                sys.stdout.write("\r" + " " * cols + "\r")
                sys.stdout.flush()
            print(f"  Skipped: {event.filename}", flush=True)

        elif event.event_type == "error":
            if show_bar and parallel <= 1:
                sys.stdout.write("\n")
                sys.stdout.flush()
            print(f"  FAILED: {event.filename}: {event.error}", flush=True)
            state["start_times"].pop(event.filename, None)

    def cleanup():
        pass

    return callback, cleanup
