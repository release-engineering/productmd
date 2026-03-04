"""``productmd verify`` subcommand — verify compose integrity."""

import json
import os
import sys
from typing import Dict

from productmd.cli import add_input_args, load_metadata, print_error
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

    # Collect all entries for progress counter
    entries = list(iter_all_locations(**metadata))
    results = {"verified": 0, "failed": 0, "skipped": 0, "errors": []}

    total = len(entries)
    for i, entry in enumerate(entries, 1):
        sys.stdout.write(f"\rVerifying: {i}/{total}")
        sys.stdout.flush()

        if entry.location is None or entry.location.checksum is None:
            results["skipped"] += 1
            continue

        # Only verify local files
        file_path = os.path.join(base_path, entry.path)
        if not os.path.isfile(file_path):
            # Try under compose/ subdirectory
            file_path = os.path.join(base_path, "compose", entry.path)

        if not os.path.isfile(file_path):
            results["skipped"] += 1
            continue

        try:
            if entry.location.verify(file_path):
                results["verified"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(
                    {
                        "path": entry.path,
                        "error": "checksum or size mismatch",
                    }
                )
        except (OSError, ValueError) as e:
            results["failed"] += 1
            results["errors"].append(
                {
                    "path": entry.path,
                    "error": str(e),
                }
            )

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
