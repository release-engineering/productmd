#!/usr/bin/env python3
"""
Mock CLI tool for developing and testing command output behaviour.

Simulates the UI of all productmd subcommands without requiring real
metadata files, network access, or Docker Compose.

Usage::

    # Simulate localize (download progress)
    python tests/mock_cli.py localize
    python tests/mock_cli.py localize --artifacts 10 --parallel 4
    python tests/mock_cli.py localize --skip 2 --fail 1

    # Simulate upgrade --compute-checksums (checksum progress)
    python tests/mock_cli.py upgrade
    python tests/mock_cli.py upgrade --artifacts 50

    # Simulate verify (verification progress)
    python tests/mock_cli.py verify
    python tests/mock_cli.py verify --artifacts 20 --fail 2

    # Simulate downgrade (instant, just a message)
    python tests/mock_cli.py downgrade
"""

import argparse
import os
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from productmd.cli.progress import make_progress_callback
from productmd.localize import DownloadEvent


# Realistic artifact paths and sizes for simulation
ARTIFACT_POOL = [
    ("Server/x86_64/iso/boot.iso", 512_000_000),
    ("Server/x86_64/iso/Fedora-Server-dvd-x86_64-41-1.0.iso", 2_465_792_000),
    ("Server/x86_64/iso/Fedora-Server-netinst-x86_64-41-1.0.iso", 891_289_600),
    ("Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm", 1_849_356),
    ("Server/x86_64/os/Packages/g/glibc-2.38-16.fc41.x86_64.rpm", 4_200_000),
    ("Server/x86_64/os/Packages/k/kernel-6.8.0-0.rc6.fc41.x86_64.rpm", 67_000_000),
    ("Server/x86_64/os/Packages/p/python3-3.13.0-1.fc41.x86_64.rpm", 28_500_000),
    ("Server/x86_64/os/GPL", 18_092),
    ("Server/x86_64/os/GPG-KEY", 3_140),
    ("Server/aarch64/iso/boot.iso", 498_000_000),
    ("Server/aarch64/iso/Fedora-Server-dvd-aarch64-41-1.0.iso", 2_100_000_000),
    ("Server/aarch64/os/Packages/b/bash-5.2.26-3.fc41.aarch64.rpm", 1_750_000),
    ("Workstation/x86_64/iso/Fedora-Workstation-Live-x86_64-41-1.0.iso", 2_200_000_000),
    ("Workstation/x86_64/os/Packages/g/gnome-shell-46.0-1.fc41.x86_64.rpm", 12_000_000),
    ("Workstation/x86_64/os/Packages/f/firefox-125.0-1.fc41.x86_64.rpm", 98_000_000),
]


def simulate_download(path, size, min_delay, max_delay, updates, callback):
    """Simulate downloading a single artifact with progress events."""
    delay = random.uniform(min_delay, max_delay)
    callback(DownloadEvent("start", path, 0, size, None))

    downloaded = 0
    chunk_size = max(1, size // updates)
    sleep_per_chunk = delay / updates

    for i in range(updates):
        time.sleep(sleep_per_chunk)
        downloaded = min(downloaded + chunk_size, size)
        callback(DownloadEvent("progress", path, downloaded, size, None))

    # Send exact final progress to ensure bar reaches 100%
    if downloaded < size:
        callback(DownloadEvent("progress", path, size, size, None))

    callback(DownloadEvent("complete", path, size, size, None))


def simulate_skip(path, callback):
    """Simulate a skipped artifact."""
    callback(DownloadEvent("skip", path, 0, None, None))


def simulate_fail(path, size, min_delay, updates, callback):
    """Simulate a failed artifact (partial download then error)."""
    callback(DownloadEvent("start", path, 0, size, None))

    # Simulate partial progress before failure
    partial_chunks = random.randint(1, max(2, updates // 4))
    chunk_size = max(1, size // updates)
    sleep_per_chunk = min_delay / updates

    for i in range(partial_chunks):
        time.sleep(sleep_per_chunk)
        callback(
            DownloadEvent(
                "progress",
                path,
                chunk_size * (i + 1),
                size,
                None,
            )
        )

    error = ConnectionError("Connection reset by peer")
    callback(
        DownloadEvent(
            "error",
            path,
            chunk_size * partial_chunks,
            size,
            error,
        )
    )


def _select_artifacts(count):
    """Select artifacts from pool, cycling and deduplicating paths."""
    artifacts = []
    for i in range(count):
        path, size = ARTIFACT_POOL[i % len(ARTIFACT_POOL)]
        if i >= len(ARTIFACT_POOL):
            cycle = i // len(ARTIFACT_POOL)
            parts = path.split("/", 1)
            path = f"{parts[0]}/{cycle}/{parts[1]}" if len(parts) > 1 else f"{cycle}/{path}"
        artifacts.append((path, size))
    random.shuffle(artifacts)
    return artifacts


def run_localize(args):
    """Simulate the localize command's download progress UI."""
    artifacts = _select_artifacts(args.artifacts)

    skip_artifacts = artifacts[: args.skip]
    fail_artifacts = artifacts[args.skip : args.skip + args.fail]
    download_artifacts = artifacts[args.skip + args.fail :]

    callback, cleanup = make_progress_callback(parallel=args.parallel)

    downloaded = 0
    skipped = 0
    failed = 0

    try:
        for path, size in skip_artifacts:
            simulate_skip(path, callback)
            skipped += 1

        if args.parallel <= 1:
            for path, size in fail_artifacts:
                simulate_fail(path, size, args.min_delay, args.updates, callback)
                failed += 1

            for path, size in download_artifacts:
                simulate_download(
                    path,
                    size,
                    args.min_delay,
                    args.max_delay,
                    args.updates,
                    callback,
                )
                downloaded += 1
        else:
            with ThreadPoolExecutor(max_workers=args.parallel) as executor:
                future_to_info = {}

                for path, size in fail_artifacts:
                    future = executor.submit(
                        simulate_fail,
                        path,
                        size,
                        args.min_delay,
                        args.updates,
                        callback,
                    )
                    future_to_info[future] = ("fail", path)

                for path, size in download_artifacts:
                    future = executor.submit(
                        simulate_download,
                        path,
                        size,
                        args.min_delay,
                        args.max_delay,
                        args.updates,
                        callback,
                    )
                    future_to_info[future] = ("download", path)

                for future in as_completed(future_to_info):
                    kind, path = future_to_info[future]
                    future.result()
                    if kind == "fail":
                        failed += 1
                    else:
                        downloaded += 1

    finally:
        cleanup()

    print(f"\nDownloaded: {downloaded}  Skipped: {skipped}  Failed: {failed}")

    if failed > 0:
        sys.exit(1)


def _fake_checksum_and_size(path, delay_min, delay_max):
    """Simulate checksum computation with a sleep. Thread-safe."""
    time.sleep(random.uniform(delay_min, delay_max))
    fake_hash = "".join(random.choices("0123456789abcdef", k=64))
    return f"sha256:{fake_hash}", random.randint(1000, 500_000_000)


def run_upgrade(args):
    """Simulate the upgrade --compute-checksums progress UI.

    Mirrors the real upgrade_to_v2() batched execution: entries are
    processed in batches of parallel_checksums size using a single
    ThreadPoolExecutor.  Each batch computes in parallel, then results
    are displayed sequentially before the next batch starts.
    """
    from productmd.cli.progress import _format_filename, _should_show_progress_bar

    show_bar = _should_show_progress_bar()
    artifacts = _select_artifacts(args.artifacts)
    total = len(artifacts)
    parallel = args.parallel_checksums
    use_parallel = parallel > 1
    batch_size = parallel if use_parallel else total

    if use_parallel:
        sys.stderr.write(f"Computing checksums with {parallel} threads...\n")

    executor = ThreadPoolExecutor(max_workers=parallel) if use_parallel else None

    try:
        for group_start in range(0, total, batch_size):
            group = artifacts[group_start : group_start + batch_size]
            group_results = {}

            # Compute checksums for this batch
            if executor is not None and len(group) > 1:
                future_to_idx = {}
                for j, (path, size) in enumerate(group):
                    future = executor.submit(_fake_checksum_and_size, path, args.min_delay, args.max_delay)
                    future_to_idx[future] = group_start + j
                for future in as_completed(future_to_idx):
                    group_results[future_to_idx[future]] = future.result()
            else:
                for j, (path, size) in enumerate(group):
                    group_results[group_start + j] = _fake_checksum_and_size(path, args.min_delay, args.max_delay)

            # Display results for this batch (sequential, in order)
            for j, (path, size) in enumerate(group):
                idx = group_start + j
                processed = idx + 1
                checksum, _ = group_results[idx]

                if show_bar:
                    try:
                        cols = os.get_terminal_size().columns
                    except (AttributeError, ValueError, OSError):
                        cols = 120
                    sys.stderr.write("\r" + " " * cols + "\r")

                sys.stderr.write(f"  {checksum}  {path}\n")

                if show_bar:
                    desc = _format_filename(path)
                    pct = int(100 * processed / total) if total > 0 else 0
                    bar_width = 20
                    filled = int(bar_width * processed / total) if total > 0 else 0
                    bar = "=" * filled + " " * (bar_width - filled)
                    sys.stderr.write(f"\rChecksumming: {processed}/{total} {pct:3d}% [{bar}]  {desc}")
                    sys.stderr.flush()
                    if processed == total:
                        sys.stderr.write("\n")
    finally:
        if executor is not None:
            executor.shutdown(wait=False)

    print("Upgraded 4 metadata file(s) to v2.0 in /tmp/v2-output")


def run_verify(args):
    """Simulate the verify command's verification progress UI.

    Mirrors the real verify batched execution: entries are processed
    in batches of parallel_checksums size using a single
    ThreadPoolExecutor.  Each batch computes in parallel, then results
    are compared and displayed sequentially.
    """
    from productmd.cli.progress import _format_filename, _should_show_progress_bar

    show_bar = _should_show_progress_bar()
    artifacts = _select_artifacts(args.artifacts)
    total = len(artifacts)
    parallel = args.parallel_checksums
    use_parallel = parallel > 1
    batch_size = parallel if use_parallel else total

    verified = 0
    failed = 0
    skipped = 0
    errors = []

    print("Loaded 4 metadata file(s) from /path/to/compose")

    if use_parallel and show_bar:
        sys.stdout.write(f"Verifying with {parallel} threads...\n")

    executor = ThreadPoolExecutor(max_workers=parallel) if use_parallel else None

    try:
        for group_start in range(0, total, batch_size):
            group = artifacts[group_start : group_start + batch_size]
            group_results = {}

            # Compute checksums for this batch
            if executor is not None and len(group) > 1:
                future_to_idx = {}
                for j, (path, size) in enumerate(group):
                    future = executor.submit(_fake_checksum_and_size, path, args.min_delay, args.max_delay)
                    future_to_idx[future] = group_start + j
                for future in as_completed(future_to_idx):
                    group_results[future_to_idx[future]] = future.result()
            else:
                for j, (path, size) in enumerate(group):
                    group_results[group_start + j] = _fake_checksum_and_size(path, args.min_delay, args.max_delay)

            # Display results for this batch (sequential, in order)
            for j, (path, size) in enumerate(group):
                idx = group_start + j
                processed = idx + 1

                # Simulate failures and skips
                if idx < args.fail:
                    failed += 1
                    errors.append(path)
                    status = "FAIL"
                    error_msg = "checksum or size mismatch"
                elif random.random() < 0.05:
                    skipped += 1
                    status = "SKIP"
                    error_msg = None
                else:
                    verified += 1
                    status = "OK"
                    error_msg = None

                if show_bar:
                    try:
                        cols = os.get_terminal_size().columns
                    except (AttributeError, ValueError, OSError):
                        cols = 120
                    sys.stdout.write("\r" + " " * cols + "\r")

                if status == "FAIL":
                    sys.stdout.write(f"  FAIL   {path}: {error_msg}\n")
                elif status == "SKIP":
                    sys.stdout.write(f"  SKIP   {path}\n")
                else:
                    sys.stdout.write(f"  OK     {path}\n")

                if show_bar:
                    desc = _format_filename(path)
                    pct = int(100 * processed / total) if total > 0 else 0
                    bar_width = 20
                    filled = int(bar_width * processed / total) if total > 0 else 0
                    bar = "=" * filled + " " * (bar_width - filled)
                    sys.stdout.write(f"\rVerifying: {processed}/{total} {pct:3d}% [{bar}]  {desc}")
                    sys.stdout.flush()
    finally:
        if executor is not None:
            executor.shutdown(wait=False)

    if show_bar:
        sys.stdout.write("\n")
    print(f"\nVerified: {verified}  Failed: {failed}  Skipped: {skipped}")

    if errors:
        print("\nFailures:")
        for path in errors:
            print(f"  {path}: checksum or size mismatch", file=sys.stderr)

    if failed > 0:
        sys.exit(1)


def run_downgrade(args):
    """Simulate the downgrade command output (instant)."""
    print("Downgraded 4 metadata file(s) to v1.2 in /tmp/v1-output")


def main():
    parser = argparse.ArgumentParser(
        prog="mock_cli",
        description="Mock CLI for testing command output behaviour",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to simulate")

    # --- localize ---
    p_localize = subparsers.add_parser("localize", help="Simulate download progress")
    p_localize.add_argument("--artifacts", type=int, default=6, help="Number of artifacts (default: 6)")
    p_localize.add_argument("--min-delay", type=float, default=0.5, help="Min download time in seconds (default: 0.5)")
    p_localize.add_argument("--max-delay", type=float, default=1.0, help="Max download time in seconds (default: 1.0)")
    p_localize.add_argument("--parallel", type=int, default=1, help="Parallel downloads (default: 1)")
    p_localize.add_argument("--skip", type=int, default=0, help="Simulated skips (default: 0)")
    p_localize.add_argument("--fail", type=int, default=0, help="Simulated failures (default: 0)")
    p_localize.add_argument("--updates", type=int, default=20, help="Progress updates per artifact (default: 20)")
    p_localize.set_defaults(func=run_localize)

    # --- upgrade ---
    p_upgrade = subparsers.add_parser("upgrade", help="Simulate checksum progress")
    p_upgrade.add_argument("--artifacts", type=int, default=20, help="Number of artifacts (default: 20)")
    p_upgrade.add_argument("--min-delay", type=float, default=0.05, help="Min delay per artifact in seconds (default: 0.05)")
    p_upgrade.add_argument("--max-delay", type=float, default=0.2, help="Max delay per artifact in seconds (default: 0.2)")
    p_upgrade.add_argument("--parallel-checksums", type=int, default=4, help="Simulated thread count (default: 4)")
    p_upgrade.set_defaults(func=run_upgrade)

    # --- verify ---
    p_verify = subparsers.add_parser("verify", help="Simulate verification progress")
    p_verify.add_argument("--artifacts", type=int, default=20, help="Number of artifacts (default: 20)")
    p_verify.add_argument("--min-delay", type=float, default=0.05, help="Min delay per artifact in seconds (default: 0.05)")
    p_verify.add_argument("--max-delay", type=float, default=0.2, help="Max delay per artifact in seconds (default: 0.2)")
    p_verify.add_argument("--fail", type=int, default=0, help="Simulated failures (default: 0)")
    p_verify.add_argument("--parallel-checksums", type=int, default=4, help="Simulated thread count (default: 4)")
    p_verify.set_defaults(func=run_verify)

    # --- downgrade ---
    p_downgrade = subparsers.add_parser("downgrade", help="Simulate downgrade output")
    p_downgrade.set_defaults(func=run_downgrade)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
