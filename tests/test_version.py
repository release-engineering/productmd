# -*- coding: utf-8 -*-

import pytest

from productmd.version import (
    VERSION_1_0,
    VERSION_1_1,
    VERSION_1_2,
    VERSION_2_0,
    DEFAULT_VERSION,
    detect_version_from_data,
    is_v1,
    is_v2,
    version_to_string,
    string_to_version,
    get_version_tuple,
    UnsupportedVersionError,
)


class TestVersionConstants:
    """Tests for version constants."""

    @pytest.mark.parametrize(
        "constant,expected",
        [
            (VERSION_1_0, (1, 0)),
            (VERSION_1_1, (1, 1)),
            (VERSION_1_2, (1, 2)),
            (VERSION_2_0, (2, 0)),
        ],
    )
    def test_version_values(self, constant, expected):
        """Test version constant values."""
        assert constant == expected

    @pytest.mark.parametrize(
        "lower,higher",
        [
            (VERSION_1_0, VERSION_1_1),
            (VERSION_1_1, VERSION_1_2),
            (VERSION_1_2, VERSION_2_0),
        ],
    )
    def test_version_ordering(self, lower, higher):
        """Test version comparison."""
        assert lower < higher

    def test_default_version(self):
        """Test default version is v2.0."""
        assert DEFAULT_VERSION == VERSION_2_0


class TestVersionConversion:
    """Tests for version conversion utilities."""

    @pytest.mark.parametrize(
        "version_tuple,expected_string",
        [
            ((1, 0), "1.0"),
            ((1, 2), "1.2"),
            ((2, 0), "2.0"),
            ((10, 5), "10.5"),
        ],
    )
    def test_version_to_string(self, version_tuple, expected_string):
        """Test converting version tuple to string."""
        assert version_to_string(version_tuple) == expected_string

    @pytest.mark.parametrize(
        "version_string,expected_tuple",
        [
            ("1.0", (1, 0)),
            ("1.2", (1, 2)),
            ("2.0", (2, 0)),
            ("10.5", (10, 5)),
            ("2.0.3", (2, 0)),  # Ignore third version number
        ],
    )
    def test_string_to_version(self, version_string, expected_tuple):
        """Test converting version string to tuple."""
        assert string_to_version(version_string) == expected_tuple

    @pytest.mark.parametrize(
        "invalid_string",
        [
            "invalid",
            "1",
            "2",
            "a.b",
            "",
        ],
    )
    def test_string_to_version_invalid(self, invalid_string):
        """Test invalid version string raises ValueError."""
        with pytest.raises(ValueError):
            string_to_version(invalid_string)

    @pytest.mark.parametrize(
        "version_input,expected",
        [
            ("2.0", (2, 0)),
            ("1.2", (1, 2)),
            ((2, 0), (2, 0)),
            ((1, 2), (1, 2)),
        ],
    )
    def test_get_version_tuple(self, version_input, expected):
        """Test normalizing version to tuple."""
        assert get_version_tuple(version_input) == expected


class TestVersionChecks:
    """Tests for version check utilities."""

    @pytest.mark.parametrize(
        "version,expected",
        [
            (VERSION_1_0, True),
            (VERSION_1_1, True),
            (VERSION_1_2, True),
            (VERSION_2_0, False),
            ("1.0", True),
            ("1.2", True),
            ("2.0", False),
            ("0.1", False),
            ((1, 5), True),
            ((2, 1), False),
        ],
    )
    def test_is_v1(self, version, expected):
        """Test v1.x detection."""
        assert is_v1(version) == expected

    @pytest.mark.parametrize(
        "version,expected",
        [
            (VERSION_1_0, False),
            (VERSION_1_1, False),
            (VERSION_1_2, False),
            (VERSION_2_0, True),
            ("1.2", False),
            ("2.0", True),
            ("0.1", False),
            ((2, 1), True),
            ((3, 0), False),  # v3.x is not v2.x
            ("2.5", True),
        ],
    )
    def test_is_v2(self, version, expected):
        """Test v2.x detection (major version == 2)."""
        assert is_v2(version) == expected


class TestVersionDetection:
    """Tests for version detection from metadata."""

    @pytest.mark.parametrize(
        "version_string,expected_tuple",
        [
            ("1.0", (1, 0)),
            ("1.1", (1, 1)),
            ("1.2", (1, 2)),
            ("2.0", (2, 0)),
        ],
    )
    def test_detect_version_from_data(self, version_string, expected_tuple):
        """Test detecting version from data with header."""
        data = {
            "header": {"version": version_string, "type": "productmd.images"},
            "payload": {"compose": {}, "images": {}},
        }
        assert detect_version_from_data(data) == expected_tuple

    @pytest.mark.parametrize(
        "invalid_data",
        [
            {"payload": {"compose": {}, "rpms": {}}},  # missing header
            {"header": {"type": "productmd.images"}, "payload": {}},  # missing version
            {"random": "data"},  # no header or payload
            {"header": {"version": "a.b", "type": "productmd.images"}},
            {},  # empty
        ],
    )
    def test_detect_version_from_data_invalid(self, invalid_data):
        """Test error on invalid data."""
        with pytest.raises(ValueError):
            detect_version_from_data(invalid_data)


class TestUnsupportedVersionError:
    """Tests for UnsupportedVersionError."""

    def test_error_message(self):
        """Test error message formatting."""
        error = UnsupportedVersionError((3, 0))
        assert "3.0" in str(error)
        assert "Unsupported" in str(error)

    def test_error_attributes(self):
        """Test error attributes."""
        error = UnsupportedVersionError((3, 0))
        assert error.version == (3, 0)
        assert (1, 2) in error.supported
        assert (2, 0) in error.supported

    def test_error_custom_supported(self):
        """Test error with custom supported versions."""
        custom_supported = [(1, 0), (2, 0)]
        error = UnsupportedVersionError((3, 0), supported=custom_supported)
        assert error.supported == custom_supported
