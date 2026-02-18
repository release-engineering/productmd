"""Tests for v2.0 RPM support with Location objects."""

import pytest

from productmd.rpms import Rpms
from productmd.location import Location
from productmd.version import VERSION_1_2, VERSION_2_0, OUTPUT_FORMAT_VERSION


def _create_rpms():
    """Create an Rpms container with compose metadata."""
    rpms = Rpms()
    rpms.compose.id = "Test-1.0-20240101.0"
    rpms.compose.date = "20240101"
    rpms.compose.type = "production"
    rpms.compose.respin = 0
    return rpms


def _add_sample_rpms(rpms):
    """Add sample RPMs to the container."""
    # binary RPM
    rpms.add(
        "Server",
        "x86_64",
        "bash-0:5.2.26-3.fc41.x86_64",
        path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
        sigkey="a15b79cc",
        category="binary",
        srpm_nevra="bash-0:5.2.26-3.fc41.src",
    )
    # source RPM
    rpms.add(
        "Server",
        "x86_64",
        "bash-0:5.2.26-3.fc41.src",
        path="Server/source/SRPMS/b/bash-5.2.26-3.fc41.src.rpm",
        sigkey="a15b79cc",
        category="source",
    )
    return rpms


class TestRpmsVersioning:
    """Tests for Rpms container version handling via VersionedMetadataMixin."""

    def test_output_version_default(self):
        """Test output_version defaults to OUTPUT_FORMAT_VERSION."""
        rpms = Rpms()
        assert rpms.output_version == OUTPUT_FORMAT_VERSION

    @pytest.mark.parametrize(
        "value, expected",
        [
            ((2, 0), (2, 0)),
            ((1, 2), (1, 2)),
            ("2.0", (2, 0)),
            ("1.2", (1, 2)),
        ],
    )
    def test_output_version_setter(self, value, expected):
        """Test output_version accepts tuples and strings."""
        rpms = Rpms()
        rpms.output_version = value
        assert rpms.output_version == expected


class TestRpmsSerialization:
    """Tests for Rpms serialization in v1.2 and v2.0 formats."""

    @pytest.mark.parametrize(
        "version, present_key, absent_key",
        [
            (VERSION_1_2, "path", "location"),
            (VERSION_2_0, "location", "path"),
        ],
    )
    def test_serialize_format_keys(self, version, present_key, absent_key):
        """Test serialization produces correct keys for each format version."""
        rpms = _create_rpms()
        _add_sample_rpms(rpms)

        data = {}
        rpms.serialize(data, force_version=version)

        # Navigate to a specific RPM entry
        rpm_entry = data["payload"]["rpms"]["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]

        assert present_key in rpm_entry, f"expected '{present_key}' in {version} output"
        assert absent_key not in rpm_entry, f"unexpected '{absent_key}' in {version} output"

    def test_serialize_v12_values(self):
        """Test v1.2 serialization produces correct field values."""
        rpms = _create_rpms()
        _add_sample_rpms(rpms)

        data = {}
        rpms.serialize(data, force_version=VERSION_1_2)

        assert data["header"]["version"] == "1.2"

        rpm = data["payload"]["rpms"]["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]
        assert rpm["path"] == "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"
        assert rpm["sigkey"] == "a15b79cc"
        assert rpm["category"] == "binary"

    def test_serialize_v20_values(self):
        """Test v2.0 serialization produces location with correct values."""
        rpms = _create_rpms()
        _add_sample_rpms(rpms)

        data = {}
        rpms.serialize(data, force_version=VERSION_2_0)

        assert data["header"]["version"] == "2.0"

        rpm = data["payload"]["rpms"]["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]
        assert "location" in rpm
        assert rpm["sigkey"] == "a15b79cc"
        assert rpm["category"] == "binary"

        loc = rpm["location"]
        assert loc["local_path"] == "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"
        # url defaults to path when no explicit location is set
        assert loc["url"] == "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"

    def test_serialize_v20_without_location_has_null_size_checksum(self):
        """Test v2.0 serialization without explicit Location produces null size/checksum."""
        rpms = _create_rpms()
        _add_sample_rpms(rpms)

        data = {}
        rpms.serialize(data, force_version=VERSION_2_0)

        rpm = data["payload"]["rpms"]["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]
        loc = rpm["location"]
        # v1.x RPM entries don't carry size or checksum, so these are null
        # when synthesized without an explicit Location
        assert loc["size"] is None
        assert loc["checksum"] is None
        assert loc["local_path"] == "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"

    def test_roundtrip_v20_with_null_size_checksum(self):
        """Test v2.0 round-trip works when size/checksum are null."""
        rpms = _create_rpms()
        _add_sample_rpms(rpms)

        # Serialize without explicit Location (size/checksum will be null)
        data1 = {}
        rpms.serialize(data1, force_version=VERSION_2_0)

        # Deserialize and re-serialize
        rpms2 = Rpms()
        rpms2.deserialize(data1)
        data2 = {}
        rpms2.serialize(data2, force_version=VERSION_2_0)

        # Payloads must match
        assert data1["payload"]["rpms"] == data2["payload"]["rpms"]

        # Verify null values survived the round-trip
        rpm = data2["payload"]["rpms"]["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]
        assert rpm["location"]["size"] is None
        assert rpm["location"]["checksum"] is None

    def test_serialize_v20_with_explicit_location(self):
        """Test v2.0 serialization with an explicitly set Location."""
        rpms = _create_rpms()
        _add_sample_rpms(rpms)

        # Attach a Location with remote URL to the RPM entry
        loc = Location(
            url="https://cdn.example.com/Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
            size=1849356,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
        )
        rpms.rpms["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]["_location"] = loc

        data = {}
        rpms.serialize(data, force_version=VERSION_2_0)

        rpm = data["payload"]["rpms"]["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]
        assert rpm["location"]["url"] == "https://cdn.example.com/Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"
        assert rpm["location"]["size"] == 1849356
        assert rpm["location"]["checksum"] == "sha256:" + "a" * 64

    def test_deserialize_v12_format(self):
        """Test deserialization from v1.2 format."""
        data = {
            "header": {"type": "productmd.rpms", "version": "1.2"},
            "payload": {
                "compose": {
                    "id": "Test-1.0-20240101.0",
                    "date": "20240101",
                    "type": "production",
                    "respin": 0,
                },
                "rpms": {
                    "Server": {
                        "x86_64": {
                            "bash-0:5.2.26-3.fc41.src": {
                                "bash-0:5.2.26-3.fc41.x86_64": {
                                    "path": "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
                                    "sigkey": "a15b79cc",
                                    "category": "binary",
                                }
                            }
                        }
                    }
                },
            },
        }

        rpms = Rpms()
        rpms.deserialize(data)

        rpm = rpms.rpms["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]
        assert rpm["path"] == "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"
        assert rpm["sigkey"] == "a15b79cc"
        assert rpm["category"] == "binary"
        # v1.x data should not have _location
        assert "_location" not in rpm

    def test_deserialize_v20_format(self):
        """Test deserialization from v2.0 format."""
        data = {
            "header": {"type": "productmd.rpms", "version": "2.0"},
            "payload": {
                "compose": {
                    "id": "Test-1.0-20240101.0",
                    "date": "20240101",
                    "type": "production",
                    "respin": 0,
                },
                "rpms": {
                    "Server": {
                        "x86_64": {
                            "bash-0:5.2.26-3.fc41.src": {
                                "bash-0:5.2.26-3.fc41.x86_64": {
                                    "location": {
                                        "url": "https://cdn.example.com/bash-5.2.26-3.fc41.x86_64.rpm",
                                        "size": 1849356,
                                        "checksum": "sha256:" + "a" * 64,
                                        "local_path": "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
                                    },
                                    "sigkey": "a15b79cc",
                                    "category": "binary",
                                }
                            }
                        }
                    }
                },
            },
        }

        rpms = Rpms()
        rpms.deserialize(data)

        rpm = rpms.rpms["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]

        # v1.x compatibility fields populated from location
        assert rpm["path"] == "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"
        assert rpm["sigkey"] == "a15b79cc"
        assert rpm["category"] == "binary"

        # Location preserved for round-trip
        assert rpm["_location"] is not None
        assert isinstance(rpm["_location"], Location)
        assert rpm["_location"].url == "https://cdn.example.com/bash-5.2.26-3.fc41.x86_64.rpm"
        assert rpm["_location"].size == 1849356

    @pytest.mark.parametrize(
        "version, header_version",
        [
            (VERSION_1_2, "1.2"),
            (VERSION_2_0, "2.0"),
        ],
    )
    def test_header_version_matches_output(self, version, header_version):
        """Test that the serialized header version matches force_version."""
        rpms = _create_rpms()
        _add_sample_rpms(rpms)

        data = {}
        rpms.serialize(data, force_version=version)

        assert data["header"]["version"] == header_version


class TestRpmsRoundTrip:
    """Tests for round-trip serialization/deserialization."""

    def test_v12_roundtrip(self):
        """Test v1.2 format round-trip preserves data."""
        rpms = _create_rpms()
        _add_sample_rpms(rpms)

        # Serialize as v1.2
        data = {}
        rpms.serialize(data, force_version=VERSION_1_2)

        # Deserialize into new object
        rpms2 = Rpms()
        rpms2.deserialize(data)

        # Verify RPM data is preserved
        rpm = rpms2.rpms["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]
        assert rpm["path"] == "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"
        assert rpm["sigkey"] == "a15b79cc"
        assert rpm["category"] == "binary"

    def test_v20_roundtrip(self):
        """Test v2.0 format round-trip preserves data including location."""
        rpms = _create_rpms()
        _add_sample_rpms(rpms)

        # Attach a remote Location
        loc = Location(
            url="https://cdn.example.com/bash-5.2.26-3.fc41.x86_64.rpm",
            size=1849356,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
        )
        rpms.rpms["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]["_location"] = loc

        # Serialize as v2.0
        data = {}
        rpms.serialize(data, force_version=VERSION_2_0)
        assert data["header"]["version"] == "2.0"

        # Deserialize into new object
        rpms2 = Rpms()
        rpms2.deserialize(data)
        assert rpms2.header.version_tuple == (2, 0)

        # Verify v1.x compatibility fields
        rpm = rpms2.rpms["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]
        assert rpm["path"] == "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"
        assert rpm["sigkey"] == "a15b79cc"
        assert rpm["category"] == "binary"

        # Verify Location round-trip
        assert rpm["_location"].url == "https://cdn.example.com/bash-5.2.26-3.fc41.x86_64.rpm"
        assert rpm["_location"].size == 1849356
        assert rpm["_location"].checksum == "sha256:" + "a" * 64

    def test_v20_roundtrip_identity(self):
        """Test v2.0 serialize-deserialize-serialize produces identical output."""
        rpms = _create_rpms()
        _add_sample_rpms(rpms)

        loc = Location(
            url="https://cdn.example.com/bash-5.2.26-3.fc41.x86_64.rpm",
            size=1849356,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
        )
        rpms.rpms["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]["_location"] = loc

        # First serialize
        data1 = {}
        rpms.serialize(data1, force_version=VERSION_2_0)

        # Deserialize and re-serialize
        rpms2 = Rpms()
        rpms2.deserialize(data1)
        data2 = {}
        rpms2.serialize(data2, force_version=VERSION_2_0)

        # Compare payload
        assert data1["payload"]["rpms"] == data2["payload"]["rpms"]
        assert data1["header"]["version"] == data2["header"]["version"]

    def test_v20_to_v12_downgrade(self):
        """Test deserializing v2.0 and re-serializing as v1.2."""
        data_v2 = {
            "header": {"type": "productmd.rpms", "version": "2.0"},
            "payload": {
                "compose": {
                    "id": "Test-1.0-20240101.0",
                    "date": "20240101",
                    "type": "production",
                    "respin": 0,
                },
                "rpms": {
                    "Server": {
                        "x86_64": {
                            "bash-0:5.2.26-3.fc41.src": {
                                "bash-0:5.2.26-3.fc41.x86_64": {
                                    "location": {
                                        "url": "https://cdn.example.com/bash.rpm",
                                        "size": 1849356,
                                        "checksum": "sha256:" + "a" * 64,
                                        "local_path": "Server/x86_64/os/Packages/b/bash.rpm",
                                    },
                                    "sigkey": "a15b79cc",
                                    "category": "binary",
                                }
                            }
                        }
                    }
                },
            },
        }

        # Load v2.0
        rpms = Rpms()
        rpms.deserialize(data_v2)

        # Serialize as v1.2
        data_v1 = {}
        rpms.serialize(data_v1, force_version=VERSION_1_2)

        assert data_v1["header"]["version"] == "1.2"
        rpm = data_v1["payload"]["rpms"]["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]
        assert "path" in rpm
        assert "location" not in rpm
        assert rpm["path"] == "Server/x86_64/os/Packages/b/bash.rpm"
        assert rpm["sigkey"] == "a15b79cc"
        assert rpm["category"] == "binary"


class TestRpmsAddWithLocation:
    """Tests for Rpms.add() with the location parameter."""

    def test_add_with_location_and_path(self):
        """Test add() with both path and location explicitly provided."""
        rpms = _create_rpms()
        loc = Location(
            url="https://cdn.example.com/Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
            size=1849356,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
        )

        rpms.add(
            "Server",
            "x86_64",
            "bash-0:5.2.26-3.fc41.x86_64",
            path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
            sigkey="a15b79cc",
            category="binary",
            srpm_nevra="bash-0:5.2.26-3.fc41.src",
            location=loc,
        )

        entry = rpms.rpms["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]
        assert entry["path"] == "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"
        assert entry["_location"] is loc
        assert entry["_location"].url == "https://cdn.example.com/Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"

    def test_add_with_location_derives_path(self):
        """Test add() with location but path=None derives path from location.local_path."""
        rpms = _create_rpms()
        loc = Location(
            url="https://cdn.example.com/Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
            size=1849356,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
        )

        rpms.add(
            "Server",
            "x86_64",
            "bash-0:5.2.26-3.fc41.x86_64",
            path=None,
            sigkey="a15b79cc",
            category="binary",
            srpm_nevra="bash-0:5.2.26-3.fc41.src",
            location=loc,
        )

        entry = rpms.rpms["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]
        assert entry["path"] == "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"
        assert entry["_location"] is loc

    def test_add_without_path_or_location_raises(self):
        """Test add() with path=None and no location raises ValueError."""
        rpms = _create_rpms()

        with pytest.raises(ValueError, match="Either 'path' or 'location' must be provided"):
            rpms.add(
                "Server",
                "x86_64",
                "bash-0:5.2.26-3.fc41.x86_64",
                path=None,
                sigkey="a15b79cc",
                category="binary",
                srpm_nevra="bash-0:5.2.26-3.fc41.src",
            )

    def test_add_with_invalid_location_type_raises(self):
        """Test add() with non-Location object raises TypeError."""
        rpms = _create_rpms()

        with pytest.raises(TypeError, match="'location' must be a Location instance"):
            rpms.add(
                "Server",
                "x86_64",
                "bash-0:5.2.26-3.fc41.x86_64",
                path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
                sigkey="a15b79cc",
                category="binary",
                srpm_nevra="bash-0:5.2.26-3.fc41.src",
                location={"url": "not a Location object"},
            )

    def test_add_with_location_serializes_v20(self):
        """Test that add() with location produces correct v2.0 output."""
        rpms = _create_rpms()
        loc = Location(
            url="https://cdn.example.com/bash-5.2.26-3.fc41.x86_64.rpm",
            size=1849356,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
        )

        rpms.add(
            "Server",
            "x86_64",
            "bash-0:5.2.26-3.fc41.x86_64",
            path=None,
            sigkey="a15b79cc",
            category="binary",
            srpm_nevra="bash-0:5.2.26-3.fc41.src",
            location=loc,
        )
        # Also add the source RPM
        rpms.add(
            "Server",
            "x86_64",
            "bash-0:5.2.26-3.fc41.src",
            path="Server/source/SRPMS/b/bash-5.2.26-3.fc41.src.rpm",
            sigkey="a15b79cc",
            category="source",
        )

        data = {}
        rpms.serialize(data, force_version=VERSION_2_0)

        rpm = data["payload"]["rpms"]["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]
        assert rpm["location"]["url"] == "https://cdn.example.com/bash-5.2.26-3.fc41.x86_64.rpm"
        assert rpm["location"]["size"] == 1849356
        assert rpm["location"]["checksum"] == "sha256:" + "a" * 64
        assert rpm["location"]["local_path"] == "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"
        assert rpm["sigkey"] == "a15b79cc"
        assert rpm["category"] == "binary"

    def test_add_with_location_serializes_v12(self):
        """Test that add() with location still produces correct v1.2 output."""
        rpms = _create_rpms()
        loc = Location(
            url="https://cdn.example.com/bash-5.2.26-3.fc41.x86_64.rpm",
            size=1849356,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
        )

        rpms.add(
            "Server",
            "x86_64",
            "bash-0:5.2.26-3.fc41.x86_64",
            path=None,
            sigkey="a15b79cc",
            category="binary",
            srpm_nevra="bash-0:5.2.26-3.fc41.src",
            location=loc,
        )
        rpms.add(
            "Server",
            "x86_64",
            "bash-0:5.2.26-3.fc41.src",
            path="Server/source/SRPMS/b/bash-5.2.26-3.fc41.src.rpm",
            sigkey="a15b79cc",
            category="source",
        )

        data = {}
        rpms.serialize(data, force_version=VERSION_1_2)

        rpm = data["payload"]["rpms"]["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]
        assert "location" not in rpm
        assert rpm["path"] == "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"
        assert rpm["sigkey"] == "a15b79cc"
        assert rpm["category"] == "binary"

    def test_add_with_location_roundtrip(self):
        """Test full round-trip: add with location -> serialize v2.0 -> deserialize -> serialize v2.0."""
        rpms = _create_rpms()
        loc = Location(
            url="https://cdn.example.com/bash-5.2.26-3.fc41.x86_64.rpm",
            size=1849356,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
        )

        rpms.add(
            "Server",
            "x86_64",
            "bash-0:5.2.26-3.fc41.x86_64",
            path=None,
            sigkey="a15b79cc",
            category="binary",
            srpm_nevra="bash-0:5.2.26-3.fc41.src",
            location=loc,
        )
        rpms.add(
            "Server",
            "x86_64",
            "bash-0:5.2.26-3.fc41.src",
            path="Server/source/SRPMS/b/bash-5.2.26-3.fc41.src.rpm",
            sigkey="a15b79cc",
            category="source",
        )

        # First serialize
        data1 = {}
        rpms.serialize(data1, force_version=VERSION_2_0)

        # Deserialize and re-serialize
        rpms2 = Rpms()
        rpms2.deserialize(data1)
        data2 = {}
        rpms2.serialize(data2, force_version=VERSION_2_0)

        # Payloads must match
        assert data1["payload"]["rpms"] == data2["payload"]["rpms"]

    def test_add_without_location_has_no_location_key(self):
        """Test that add() without location does not store _location key."""
        rpms = _create_rpms()
        rpms.add(
            "Server",
            "x86_64",
            "bash-0:5.2.26-3.fc41.x86_64",
            path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
            sigkey="a15b79cc",
            category="binary",
            srpm_nevra="bash-0:5.2.26-3.fc41.src",
        )

        entry = rpms.rpms["Server"]["x86_64"]["bash-0:5.2.26-3.fc41.src"]["bash-0:5.2.26-3.fc41.x86_64"]
        assert "_location" not in entry
