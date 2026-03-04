"""
CLI tools for productmd metadata operations.

Provides a single ``productmd`` command with subcommands for upgrading,
downgrading, localizing, and verifying compose metadata.

Input auto-detection: if the input is a file, it is loaded as a single
metadata file.  If it is a directory, it is treated as a compose
directory and scanned for metadata.  Remote URLs are not supported.

Usage::

    productmd upgrade --output /tmp/v2 --base-url https://cdn/ images.json
    productmd upgrade --output /tmp/v2 --base-url https://cdn/ /path/to/compose
    productmd downgrade --output /tmp/v1 rpms.json
    productmd localize --output /mnt/local images.json
    productmd verify /path/to/compose
"""

import argparse
import json
import logging
import os
import sys
from typing import Dict, Optional, Tuple

from productmd.compose import Compose

__all__ = (
    "add_input_args",
    "load_compose_dir",
    "load_metadata",
    "load_single_file",
    "main",
    "print_error",
)

logger = logging.getLogger(__name__)


def load_single_file(file_path: str) -> Dict[str, object]:
    """
    Load a single metadata file by detecting its type from the header.

    :param file_path: Path to a JSON metadata file
    :type file_path: str
    :return: Dict with a single key mapping module name to metadata object
    :rtype: Dict[str, object]
    :raises ValueError: If the file type is unknown
    :raises FileNotFoundError: If the file does not exist
    """
    from productmd.composeinfo import ComposeInfo
    from productmd.extra_files import ExtraFiles
    from productmd.images import Images
    from productmd.modules import Modules
    from productmd.rpms import Rpms

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"No such file: {file_path}")

    with open(file_path) as f:
        data = json.load(f)

    header_type = data.get("header", {}).get("type", "")
    type_map = {
        "productmd.composeinfo": ("composeinfo", ComposeInfo),
        "productmd.images": ("images", Images),
        "productmd.rpms": ("rpms", Rpms),
        "productmd.modules": ("modules", Modules),
        "productmd.extra_files": ("extra_files", ExtraFiles),
    }

    if header_type not in type_map:
        raise ValueError(f"Unknown metadata type: {header_type}")

    key, cls = type_map[header_type]
    obj = cls()
    obj.deserialize(data)
    return {key: obj}


def load_compose_dir(compose_path: str) -> Tuple[Dict[str, object], str]:
    """
    Load all metadata from a compose directory.

    Uses the :class:`~productmd.compose.Compose` class to scan for
    metadata files under the ``metadata/`` subdirectory.

    :param compose_path: Path to a compose root directory
    :type compose_path: str
    :return: Tuple of (metadata dict, resolved compose path)
    :rtype: tuple
    """
    if not os.path.isdir(compose_path):
        raise NotADirectoryError(f"No such directory: {compose_path}")

    compose = Compose(compose_path)
    result = {}

    for name, prop in [
        ("composeinfo", "info"),
        ("images", "images"),
        ("rpms", "rpms"),
        ("modules", "modules"),
        ("extra_files", "extra_files"),
    ]:
        try:
            result[name] = getattr(compose, prop)
        except RuntimeError as e:
            logger.debug("Skipping %s: %s", name, e)

    if not result:
        raise RuntimeError(f"Directory does not appear to be a compose: no metadata found in {compose_path}")

    return result, compose.compose_path


def add_input_args(parser: object) -> None:
    """
    Add the positional input argument common to all subcommands.

    :param parser: argparse subcommand parser
    :type parser: object
    """
    parser.add_argument(
        "input",
        help="Path to a metadata file or compose directory",
    )


def _discover_compose_root(file_path: str) -> Optional[str]:
    """
    Try to find a compose root from a metadata file's location.

    Checks standard compose layouts:

    - ``<root>/metadata/<file>`` → try ``Compose(<root>)``
    - ``<root>/<file>`` → try ``Compose(<root>)``

    The compose root is validated by checking that at least one
    metadata file (``composeinfo.json``) exists under it.

    :param file_path: Path to a metadata file
    :type file_path: str
    :return: Resolved compose path, or ``None`` if not found
    :rtype: str or None
    """
    parent = os.path.dirname(os.path.abspath(file_path))

    candidates = []
    # Standard layout: <root>/metadata/images.json
    if os.path.basename(parent) == "metadata":
        candidates.append(os.path.dirname(parent))
    # Try parent directly
    candidates.append(parent)

    for candidate in candidates:
        try:
            compose = Compose(candidate)
            # Validate that this is actually a compose — try to load composeinfo
            compose.info  # noqa: B018 — triggers metadata file lookup
            return compose.compose_path
        except (RuntimeError, OSError):
            continue

    return None


def load_metadata(args: object) -> Dict[str, object]:
    """
    Load metadata based on parsed CLI arguments.

    Auto-detects whether the input is a file or directory:

    - **File**: loads a single metadata file and tries to discover the
      compose root from its location (stored as ``args._compose_path``).
    - **Directory**: loads all metadata from the compose directory
      (stored as ``args._compose_path``).

    Remote URLs are rejected.

    :param args: Parsed argparse namespace with ``input``
    :type args: object
    :return: Dict of metadata objects keyed by module name
    :rtype: Dict[str, object]
    """
    path = args.input

    # Reject remote URLs — all inputs must be local
    if path.startswith(("http://", "https://")):
        raise ValueError(
            "Remote URLs are not supported as input. "
            "Download the metadata files first:\n"
            f"  curl -o metadata.json {path}\n"
            f"  productmd <command> metadata.json ..."
        )

    if os.path.isfile(path):
        result = load_single_file(path)
        args._compose_path = _discover_compose_root(path)
        return result
    elif os.path.isdir(path):
        result, compose_path = load_compose_dir(path)
        args._compose_path = compose_path
        return result
    else:
        raise FileNotFoundError(f"No such file or directory: {path}")


def print_error(msg: str) -> None:
    """Print an error message to stderr.

    :param msg: Error message to display
    :type msg: str
    """
    print(f"Error: {msg}", file=sys.stderr)


def main() -> None:
    """Entry point for the ``productmd`` CLI tool."""
    parser = argparse.ArgumentParser(
        prog="productmd",
        description="productmd metadata tools for compose management",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Register subcommands
    from productmd.cli.upgrade import register as register_upgrade
    from productmd.cli.downgrade import register as register_downgrade
    from productmd.cli.localize import register as register_localize
    from productmd.cli.verify import register as register_verify

    register_upgrade(subparsers)
    register_downgrade(subparsers)
    register_localize(subparsers)
    register_verify(subparsers)

    args = parser.parse_args()

    # Python 3.6 compat: subparsers doesn't support required=True
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except KeyboardInterrupt:
        print_error("Interrupted")
        sys.exit(130)
    except (ValueError, FileNotFoundError, NotADirectoryError, OSError, RuntimeError) as e:
        print_error(str(e))
        sys.exit(1)
