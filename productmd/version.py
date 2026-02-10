# Copyright (C) 2024  Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

"""
This module provides version detection and handling utilities for ProductMD metadata.

ProductMD supports multiple metadata format versions:

- **v1.x** (1.0, 1.1, 1.2): Local compose format with relative paths
- **v2.0**: Distributed compose format with Location objects

This module provides utilities to:
- Detect the version of parsed metadata
- Check version compatibility
- Convert between version representations

Example::

    from productmd.version import (
        detect_version_from_data,
        is_v1,
        is_v2,
        VERSION_1_2,
        VERSION_2_0,
        DEFAULT_VERSION,
    )

    # Detect version from parsed JSON data
    data = {"header": {"version": "2.0", "type": "productmd.images"}, "payload": {}}
    version = detect_version_from_data(data)
    print(version)  # (2, 0)

    # Check version type
    if is_v2(version):
        print("This is a v2.0 distributed compose")
    elif is_v1(version):
        print("This is a v1.x local compose")

    # Version constants
    print(VERSION_2_0)  # (2, 0)
    print(DEFAULT_VERSION)  # (2, 0) - default for new files
"""

from typing import Tuple, Union, Optional, Any, Dict

__all__ = (
    "VERSION_1_0",
    "VERSION_1_1",
    "VERSION_1_2",
    "VERSION_2_0",
    "DEFAULT_VERSION",
    "detect_version_from_data",
    "is_v1",
    "is_v2",
    "get_version_tuple",
    "version_to_string",
    "string_to_version",
    "VersionError",
    "UnsupportedVersionError",
)


# Version constants
VERSION_1_0: Tuple[int, int] = (1, 0)
VERSION_1_1: Tuple[int, int] = (1, 1)
VERSION_1_2: Tuple[int, int] = (1, 2)
VERSION_2_0: Tuple[int, int] = (2, 0)

# Current default version for writing new files
DEFAULT_VERSION: Tuple[int, int] = VERSION_2_0

# Minimum version that supports Location objects
MIN_LOCATION_VERSION: Tuple[int, int] = VERSION_2_0


class VersionError(Exception):
    """Base exception for version-related errors."""

    pass


class UnsupportedVersionError(VersionError):
    """Raised when a metadata file has an unsupported version."""

    def __init__(self, version: Tuple[int, int], supported: list = None):
        self.version = version
        self.supported = supported or [VERSION_1_0, VERSION_1_1, VERSION_1_2, VERSION_2_0]
        super().__init__(
            f"Unsupported metadata version: {version_to_string(version)}. "
            f"Supported versions: {', '.join(version_to_string(v) for v in self.supported)}"
        )


def version_to_string(version: Tuple[int, int]) -> str:
    """
    Convert a version tuple to a string.

    :param version: Version tuple (major, minor)
    :type version: tuple
    :return: Version string like "2.0"
    :rtype: str
    """
    return f"{version[0]}.{version[1]}"


def string_to_version(version_str: str) -> Tuple[int, int]:
    """
    Convert a version string to a tuple.

    :param version_str: Version string like "2.0"
    :type version_str: str
    :return: Version tuple (major, minor)
    :rtype: tuple
    :raises ValueError: If version string is invalid
    """
    try:
        parts = version_str.split(".")
        return (int(parts[0]), int(parts[1]))
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid version string: {version_str}") from e


def get_version_tuple(version: Union[str, Tuple[int, int]]) -> Tuple[int, int]:
    """
    Normalize version to a tuple.

    :param version: Version as string or tuple
    :type version: str or tuple
    :return: Version tuple (major, minor)
    :rtype: tuple
    """
    if isinstance(version, str):
        return string_to_version(version)
    return version


def is_v1(version: Union[str, Tuple[int, int]]) -> bool:
    """
    Check if version is v1.x (1.0, 1.1, 1.2).

    :param version: Version to check
    :type version: str or tuple
    :return: True if v1.x
    :rtype: bool
    """
    v = get_version_tuple(version)
    return v[0] == 1


def is_v2(version: Union[str, Tuple[int, int]]) -> bool:
    """
    Check if version is v2.x (2.0+).

    :param version: Version to check
    :type version: str or tuple
    :return: True if v2.x
    :rtype: bool
    """
    v = get_version_tuple(version)
    return v[0] == 2


def supports_location_objects(version: Union[str, Tuple[int, int]]) -> bool:
    """
    Check if version supports Location objects.

    :param version: Version to check
    :type version: str or tuple
    :return: True if Location objects are supported
    :rtype: bool
    """
    v = get_version_tuple(version)
    return v >= MIN_LOCATION_VERSION


def detect_version_from_data(data: Dict[str, Any]) -> Tuple[int, int]:
    """
    Detect the version from parsed metadata.

    :param data: Parsed JSON data
    :type data: dict
    :return: Version tuple (major, minor)
    :rtype: tuple
    :raises ValueError: If version cannot be determined
    """
    # Check for header.version (standard location)
    if "header" in data and "version" in data["header"]:
        return string_to_version(data["header"]["version"])

    raise ValueError("Cannot determine metadata version from data")


class VersionedMetadataMixin:
    """
    Mixin class providing version-aware serialization/deserialization.

    This mixin can be added to metadata classes to provide automatic
    version detection and handling.

    Usage::

        class MyMetadata(MetadataBase, VersionedMetadataMixin):
            def deserialize(self, data):
                version = self.detect_data_version(data)
                if is_v2(version):
                    self.deserialize_2_0(data)
                else:
                    self.deserialize_1_x(data)
    """

    # Default output version (can be overridden per-class or per-instance)
    _output_version: Optional[Tuple[int, int]] = None

    @property
    def output_version(self) -> Tuple[int, int]:
        """
        Get the version to use when serializing.

        :return: Version tuple
        :rtype: tuple
        """
        if self._output_version is not None:
            return self._output_version
        # Enforce distributed compose
        return DEFAULT_VERSION

    @output_version.setter
    def output_version(self, version: Union[str, Tuple[int, int]]):
        """
        Set the version to use when serializing.

        :param version: Version to use
        :type version: str or tuple
        """
        self._output_version = get_version_tuple(version)

    def detect_data_version(self, data: Dict[str, Any]) -> Tuple[int, int]:
        """
        Detect version from parsed data.

        :param data: Parsed metadata
        :type data: dict
        :return: Version tuple
        :rtype: tuple
        """
        return detect_version_from_data(data)

    def should_use_locations(self) -> bool:
        """
        Check if Location objects should be used for output.

        :return: True if using v2.0 format
        :rtype: bool
        """
        return supports_location_objects(self.output_version)
