"""``productmd verify`` subcommand — verify compose integrity."""

import json
import os
import sys
from typing import Dict

from productmd.cli import add_input_args, load_metadata, print_error
from productmd.cli.progress import _format_filename, _should_show_progress_bar
from productmd.convert import iter_all_locations


def register(subparsers: object) -> None:
    """Register the verify subcommand.

    :param subparsers: argparse subparsers action
    :type subparsers: object
    """
    parser = subparsers.add_parser(
        "verify",
        help="Verify integrity of compose metadata and local artifacts",
        description=(
            "Verify that local compose artifacts match their metadata. "
            "Checks checksums and file sizes for all artifacts with "
            "Location objects. Only verifies local files."
        ),
    )
    parser.add_argument(
        "--report",
        help="Output JSON report file with verification results",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Only verify metadata loads correctly, skip artifact checksums",
    )
    parser.add_argument(
        "--parallel-checksums",
        type=int,
        default=4,
        help="Number of threads for checksum verification (default: 4)",
    )
    add_input_args(parser)
    parser.set_defaults(func=run)


def run(args: object) -> None:
    """Execute the verify subcommand.

    :param args: Parsed argparse namespace
    :type args: object
    """
    metadata = load_metadata(args)
    if not metadata:
        print_error(f"No metadata found at {args.input}")
        sys.exit(1)

    print(f"Loaded {len(metadata)} metadata file(s) from {args.input}")

    if args.quick:
        print("Quick mode: metadata loaded successfully, skipping artifact verification")
        if args.report:
            _write_report(
                args.report,
                {
                    "verified": 0,
                    "failed": 0,
                    "skipped": len(list(iter_all_locations(**metadata))),
                    "errors": [],
                },
            )
        return

    # Artifact checksum verification requires knowing the compose root.
    # Auto-detected from the input path via load_metadata().
    compose_path = getattr(args, "_compose_path", None)
    if compose_path is None:
        print("Could not determine compose root: skipping artifact verification")
        if args.report:
            _write_report(
                args.report,
                {
                    "verified": 0,
                    "failed": 0,
                    "skipped": len(list(iter_all_locations(**metadata))),
                    "errors": [],
                },
            )
        return

    base_path = compose_path
    parallel_checksums = args.parallel_checksums

    # Collect all entries for progress counter
    entries = list(iter_all_locations(**metadata))
    results = {"verified": 0, "failed": 0, "skipped": 0, "errors": []}

    show_bar = _should_show_progress_bar()
    total = len(entries)

    from concurrent.futures import ThreadPoolExecutor, as_completed

    from productmd.convert import _compute_checksum_and_size

    # Pre-resolve file paths and classify entries
    entry_info = []  # [(file_path_or_None, skip_reason_or_None), ...]
    for entry in entries:
        if entry.location is None or entry.location.checksum is None:
            entry_info.append((None, "no checksum"))
        else:
            file_path = os.path.join(base_path, entry.path)
            if not os.path.isfile(file_path):
                file_path = os.path.join(base_path, "compose", entry.path)
            if not os.path.isfile(file_path):
                entry_info.append((None, "file not found"))
            else:
                entry_info.append((file_path, None))

    # Process entries in batches for interleaved parallel checksums.
    # Each batch computes checksums in parallel, then displays results
    # before the next batch starts.
    use_parallel = parallel_checksums > 1
    batch_size = parallel_checksums if use_parallel else max(total, 1)

    if use_parallel and show_bar:
        sys.stdout.write(f"Verifying with {parallel_checksums} threads...\n")

    executor = ThreadPoolExecutor(max_workers=parallel_checksums) if use_parallel else None

    try:
        for group_start in range(0, total, batch_size):
            group_end = min(group_start + batch_size, total)
            group_checksums = {}

            # Compute checksums for verifiable entries in this batch
            tasks_in_group = []
            for idx in range(group_start, group_end):
                file_path, skip_reason = entry_info[idx]
                if skip_reason is None and file_path is not None:
                    tasks_in_group.append((idx, file_path))

            if executor is not None and len(tasks_in_group) > 1:
                future_to_index = {}
                for idx, file_path in tasks_in_group:
                    future = executor.submit(_compute_checksum_and_size, file_path)
                    future_to_index[future] = idx
                for future in as_completed(future_to_index):
                    idx = future_to_index[future]
                    try:
                        group_checksums[idx] = future.result()
                    except (OSError, ValueError) as e:
                        group_checksums[idx] = (None, None, str(e))
            else:
                for idx, file_path in tasks_in_group:
                    try:
                        group_checksums[idx] = _compute_checksum_and_size(file_path)
                    except (OSError, ValueError) as e:
                        group_checksums[idx] = (None, None, str(e))

            # Display results for this batch (sequential, in order)
            for idx in range(group_start, group_end):
                entry = entries[idx]
                processed = idx + 1
                status = None
                error_msg = None
                file_path, skip_reason = entry_info[idx]

                if skip_reason is not None:
                    results["skipped"] += 1
                    status = "SKIP"
                elif idx in group_checksums:
                    result_data = group_checksums[idx]
                    if len(result_data) == 3:
                        results["failed"] += 1
                        error_msg = result_data[2]
                        results["errors"].append({"path": entry.path, "error": error_msg})
                        status = "FAIL"
                    else:
                        computed_checksum, computed_size = result_data
                        checksum_ok = entry.location.checksum == computed_checksum
                        size_ok = entry.location.size is None or entry.location.size == computed_size
                        if checksum_ok and size_ok:
                            results["verified"] += 1
                            status = "OK"
                        else:
                            results["failed"] += 1
                            error_msg = "checksum or size mismatch"
                            results["errors"].append({"path": entry.path, "error": error_msg})
                            status = "FAIL"

                if show_bar:
                    try:
                        cols = os.get_terminal_size().columns
                    except (AttributeError, ValueError, OSError):
                        cols = 120
                    sys.stdout.write("\r" + " " * cols + "\r")

                if status == "FAIL":
                    sys.stdout.write(f"  FAIL   {entry.path}: {error_msg}\n")
                elif status == "SKIP":
                    sys.stdout.write(f"  SKIP   {entry.path}\n")
                else:
                    sys.stdout.write(f"  OK     {entry.path}\n")

                if show_bar:
                    desc = _format_filename(entry.path)
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
        sys.stdout.flush()

    # Print summary
    print(f"\nVerified: {results['verified']}  Failed: {results['failed']}  Skipped: {results['skipped']}")

    if results["errors"]:
        print("\nFailures:")
        for err in results["errors"]:
            print(f"  {err['path']}: {err['error']}", file=sys.stderr)

    if args.report:
        _write_report(args.report, results)
        print(f"Report written to {args.report}")

    if results["failed"] > 0:
        sys.exit(1)


def _write_report(report_path: str, results: Dict[str, object]) -> None:
    """Write verification results to a JSON file.

    :param report_path: Path to the output JSON report
    :type report_path: str
    :param results: Verification results dict
    :type results: Dict[str, object]
    """
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
