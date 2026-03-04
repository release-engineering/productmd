"""``productmd upgrade`` subcommand — upgrade v1.2 metadata to v2.0."""

import json
import sys
from typing import Callable

from productmd.cli import add_input_args, load_metadata, print_error
from productmd.convert import upgrade_to_v2


def _load_url_mapper(url_map_path: str) -> Callable:
    """
    Load a URL mapping function from a JSON file.

    The JSON file should contain per-type URL templates::

        {
            "rpm": "https://cdn.example.com/rpms/{path}",
            "image": "https://cdn.example.com/images/{path}",
            "module": "https://cdn.example.com/modules/{path}",
            "extra_file": "https://cdn.example.com/extra/{path}",
            "variant_path": "https://cdn.example.com/repos/{path}",
            "default": "https://cdn.example.com/{path}"
        }

    Templates use ``{path}``, ``{variant}``, ``{arch}``, and
    ``{metadata_type}`` as placeholders.

    :param url_map_path: Path to JSON file
    :type url_map_path: str
    :return: URL mapper callable
    :rtype: Callable
    """
    with open(url_map_path) as f:
        url_map = json.load(f)

    def mapper(local_path, variant, arch, metadata_type):
        template = url_map.get(metadata_type, url_map.get("default", "{path}"))
        return template.format(
            path=local_path,
            variant=variant,
            arch=arch,
            metadata_type=metadata_type,
        )

    return mapper


def register(subparsers: object) -> None:
    """Register the upgrade subcommand.

    :param subparsers: argparse subparsers action
    :type subparsers: object
    """
    parser = subparsers.add_parser(
        "upgrade",
        help="Upgrade v1.2 compose metadata to v2.0 format",
        description=("Load v1.2 compose metadata, create Location objects for each artifact, and write v2.0 metadata files."),
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory for v2.0 metadata files",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="Base URL prefix for remote artifact URLs",
    )
    parser.add_argument(
        "--compute-checksums",
        action="store_true",
        help="Compute SHA-256 checksums from local files",
    )
    parser.add_argument(
        "--url-map",
        help="JSON file with per-type URL mapping templates",
    )
    add_input_args(parser)
    parser.set_defaults(func=run)


def run(args: object) -> None:
    """Execute the upgrade subcommand.

    :param args: Parsed argparse namespace
    :type args: object
    """
    metadata = load_metadata(args)
    if not metadata:
        print_error(f"No metadata found at {args.input}")
        sys.exit(1)

    compose_path = getattr(args, "_compose_path", None)

    if args.compute_checksums and compose_path is None:
        print_error("Cannot compute checksums: could not determine compose root from input path. Pass a compose directory as input.")
        sys.exit(1)

    url_mapper = None
    if args.url_map:
        try:
            url_mapper = _load_url_mapper(args.url_map)
        except (OSError, json.JSONDecodeError) as e:
            print_error(f"Failed to load URL map: {e}")
            sys.exit(1)

    result = upgrade_to_v2(
        output_dir=args.output,
        base_url=args.base_url,
        compute_checksums=args.compute_checksums,
        compose_path=compose_path,
        url_mapper=url_mapper,
        **metadata,
    )

    print(f"Upgraded {len(result)} metadata file(s) to v2.0 in {args.output}")
