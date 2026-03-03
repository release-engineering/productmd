"""``productmd downgrade`` subcommand — downgrade v2.0 metadata to v1.2."""

import sys

from productmd.cli import add_input_args, load_metadata, print_error
from productmd.convert import downgrade_to_v1


def register(subparsers: object) -> None:
    """Register the downgrade subcommand.

    :param subparsers: argparse subparsers action
    :type subparsers: object
    """
    parser = subparsers.add_parser(
        "downgrade",
        help="Downgrade v2.0 compose metadata to v1.2 format",
        description=(
            "Load v2.0 compose metadata and write v1.2 metadata files "
            "using Location.local_path as the path values. "
            "Metadata-only — does not download artifacts."
        ),
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory for v1.2 metadata files",
    )
    add_input_args(parser)
    parser.set_defaults(func=run)


def run(args: object) -> None:
    """Execute the downgrade subcommand.

    :param args: Parsed argparse namespace
    :type args: object
    """
    metadata = load_metadata(args)
    if not metadata:
        print_error(f"No metadata found at {args.input}")
        sys.exit(1)

    result = downgrade_to_v1(
        output_dir=args.output,
        **metadata,
    )

    print(f"Downgraded {len(result)} metadata file(s) to v1.2 in {args.output}")
