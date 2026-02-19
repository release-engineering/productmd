"""Tests for v2.0 ExtraFiles support with Location objects."""

import pytest

from productmd.extra_files import ExtraFiles
from productmd.location import Location
from productmd.version import VERSION_1_2, VERSION_2_0, OUTPUT_FORMAT_VERSION


def _create_extra_files():
    """Create an ExtraFiles container with compose metadata."""
    ef = ExtraFiles()
    ef.compose.id = "Test-1.0-20240101.0"
    ef.compose.date = "20240101"
    ef.compose.type = "production"
    ef.compose.respin = 0
    return ef


def _add_sample_files(ef):
    """Add sample extra files to the container."""
    ef.add(
        "Server",
        "x86_64",
        "Server/x86_64/os/GPL",
        size=18092,
        checksums={"sha256": "a" * 64},
    )
    ef.add(
        "Server",
        "x86_64",
        "Server/x86_64/os/EULA",
        size=2547,
        checksums={"sha256": "b" * 64},
    )
    return ef


class TestExtraFilesVersioning:
    """Tests for ExtraFiles container version handling via VersionedMetadataMixin."""

    def test_output_version_default(self):
        """Test output_version defaults to OUTPUT_FORMAT_VERSION."""
        ef = ExtraFiles()
        assert ef.output_version == OUTPUT_FORMAT_VERSION

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
        ef = ExtraFiles()
        ef.output_version = value
        assert ef.output_version == expected


class TestExtraFilesSerialization:
    """Tests for ExtraFiles serialization in v1.2 and v2.0 formats."""

    @pytest.mark.parametrize(
        "version, present_key, absent_keys",
        [
            (VERSION_1_2, "checksums", ["location"]),
            (VERSION_2_0, "location", ["checksums", "size"]),
        ],
    )
    def test_serialize_format_keys(self, version, present_key, absent_keys):
        """Test serialization produces correct keys for each format version."""
        ef = _create_extra_files()
        _add_sample_files(ef)

        data = {}
        ef.serialize(data, force_version=version)

        entry = data["payload"]["extra_files"]["Server"]["x86_64"][0]
        assert "file" in entry
        assert present_key in entry, f"expected '{present_key}' in {version} output"
        for key in absent_keys:
            assert key not in entry, f"unexpected '{key}' in {version} output"

    def test_serialize_v12_values(self):
        """Test v1.2 serialization produces correct field values."""
        ef = _create_extra_files()
        _add_sample_files(ef)

        data = {}
        ef.serialize(data, force_version=VERSION_1_2)

        assert data["header"]["version"] == "1.2"

        entry = data["payload"]["extra_files"]["Server"]["x86_64"][0]
        assert entry["file"] == "Server/x86_64/os/GPL"
        assert entry["size"] == 18092
        assert entry["checksums"] == {"sha256": "a" * 64}

    def test_serialize_v20_values(self):
        """Test v2.0 serialization produces location with correct values."""
        ef = _create_extra_files()
        _add_sample_files(ef)

        data = {}
        ef.serialize(data, force_version=VERSION_2_0)

        assert data["header"]["version"] == "2.0"

        entry = data["payload"]["extra_files"]["Server"]["x86_64"][0]
        assert entry["file"] == "GPL"  # basename only in v2.0

        loc = entry["location"]
        assert loc["local_path"] == "Server/x86_64/os/GPL"
        assert loc["size"] == 18092
        assert loc["checksum"] == "sha256:" + "a" * 64

    def test_serialize_v20_with_explicit_location(self):
        """Test v2.0 serialization with an explicitly set Location."""
        ef = _create_extra_files()
        _add_sample_files(ef)

        # Attach a Location with remote URL to the first entry
        loc = Location(
            url="https://cdn.example.com/Server/x86_64/os/GPL",
            size=18092,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/GPL",
        )
        ef.extra_files["Server"]["x86_64"][0]["_location"] = loc

        data = {}
        ef.serialize(data, force_version=VERSION_2_0)

        entry = data["payload"]["extra_files"]["Server"]["x86_64"][0]
        assert entry["location"]["url"] == "https://cdn.example.com/Server/x86_64/os/GPL"
        assert entry["location"]["size"] == 18092

    def test_deserialize_v12_format(self):
        """Test deserialization from v1.2 format."""
        data = {
            "header": {"type": "productmd.extra_files", "version": "1.2"},
            "payload": {
                "compose": {
                    "id": "Test-1.0-20240101.0",
                    "date": "20240101",
                    "type": "production",
                    "respin": 0,
                },
                "extra_files": {
                    "Server": {
                        "x86_64": [
                            {
                                "file": "Server/x86_64/os/GPL",
                                "size": 18092,
                                "checksums": {"sha256": "a" * 64},
                            }
                        ]
                    }
                },
            },
        }

        ef = ExtraFiles()
        ef.deserialize(data)

        entry = ef.extra_files["Server"]["x86_64"][0]
        assert entry["file"] == "Server/x86_64/os/GPL"
        assert entry["size"] == 18092
        assert entry["checksums"] == {"sha256": "a" * 64}
        # v1.x data should not have _location
        assert "_location" not in entry

    def test_deserialize_v20_format(self):
        """Test deserialization from v2.0 format."""
        data = {
            "header": {"type": "productmd.extra_files", "version": "2.0"},
            "payload": {
                "compose": {
                    "id": "Test-1.0-20240101.0",
                    "date": "20240101",
                    "type": "production",
                    "respin": 0,
                },
                "extra_files": {
                    "Server": {
                        "x86_64": [
                            {
                                "file": "GPL",
                                "location": {
                                    "url": "https://cdn.example.com/Server/x86_64/os/GPL",
                                    "size": 18092,
                                    "checksum": "sha256:" + "a" * 64,
                                    "local_path": "Server/x86_64/os/GPL",
                                },
                            }
                        ]
                    }
                },
            },
        }

        ef = ExtraFiles()
        ef.deserialize(data)

        entry = ef.extra_files["Server"]["x86_64"][0]

        # v1.x compatibility fields populated from location
        assert entry["file"] == "Server/x86_64/os/GPL"
        assert entry["size"] == 18092
        assert entry["checksums"] == {"sha256": "a" * 64}

        # Location preserved for round-trip
        assert entry["_location"] is not None
        assert isinstance(entry["_location"], Location)
        assert entry["_location"].url == "https://cdn.example.com/Server/x86_64/os/GPL"

    @pytest.mark.parametrize(
        "version, header_version",
        [
            (VERSION_1_2, "1.2"),
            (VERSION_2_0, "2.0"),
        ],
    )
    def test_header_version_matches_output(self, version, header_version):
        """Test that the serialized header version matches force_version."""
        ef = _create_extra_files()
        _add_sample_files(ef)

        data = {}
        ef.serialize(data, force_version=version)

        assert data["header"]["version"] == header_version


class TestExtraFilesRoundTrip:
    """Tests for round-trip serialization/deserialization."""

    def test_v12_roundtrip(self):
        """Test v1.2 format round-trip preserves data."""
        ef = _create_extra_files()
        _add_sample_files(ef)

        # Serialize as v1.2
        data = {}
        ef.serialize(data, force_version=VERSION_1_2)

        # Deserialize into new object
        ef2 = ExtraFiles()
        ef2.deserialize(data)

        # Verify data is preserved
        entry = ef2.extra_files["Server"]["x86_64"][0]
        assert entry["file"] == "Server/x86_64/os/GPL"
        assert entry["size"] == 18092
        assert entry["checksums"] == {"sha256": "a" * 64}

    def test_v20_roundtrip(self):
        """Test v2.0 format round-trip preserves data including location."""
        ef = _create_extra_files()
        _add_sample_files(ef)

        # Attach a remote Location to first entry
        loc = Location(
            url="https://cdn.example.com/Server/x86_64/os/GPL",
            size=18092,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/GPL",
        )
        ef.extra_files["Server"]["x86_64"][0]["_location"] = loc

        # Serialize as v2.0
        data = {}
        ef.serialize(data, force_version=VERSION_2_0)
        assert data["header"]["version"] == "2.0"

        # Deserialize into new object
        ef2 = ExtraFiles()
        ef2.deserialize(data)
        assert ef2.header.version_tuple == (2, 0)

        # Verify v1.x compatibility fields
        entry = ef2.extra_files["Server"]["x86_64"][0]
        assert entry["file"] == "Server/x86_64/os/GPL"
        assert entry["size"] == 18092
        assert entry["checksums"] == {"sha256": "a" * 64}

        # Verify Location round-trip
        assert entry["_location"].url == "https://cdn.example.com/Server/x86_64/os/GPL"
        assert entry["_location"].size == 18092

    def test_v20_roundtrip_identity(self):
        """Test v2.0 serialize-deserialize-serialize produces identical output."""
        ef = _create_extra_files()
        _add_sample_files(ef)

        loc = Location(
            url="https://cdn.example.com/Server/x86_64/os/GPL",
            size=18092,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/GPL",
        )
        ef.extra_files["Server"]["x86_64"][0]["_location"] = loc

        # First serialize
        data1 = {}
        ef.serialize(data1, force_version=VERSION_2_0)

        # Deserialize and re-serialize
        ef2 = ExtraFiles()
        ef2.deserialize(data1)
        data2 = {}
        ef2.serialize(data2, force_version=VERSION_2_0)

        # Compare payload
        assert data1["payload"]["extra_files"] == data2["payload"]["extra_files"]
        assert data1["header"]["version"] == data2["header"]["version"]

    def test_v20_to_v12_downgrade(self):
        """Test deserializing v2.0 and re-serializing as v1.2."""
        data_v2 = {
            "header": {"type": "productmd.extra_files", "version": "2.0"},
            "payload": {
                "compose": {
                    "id": "Test-1.0-20240101.0",
                    "date": "20240101",
                    "type": "production",
                    "respin": 0,
                },
                "extra_files": {
                    "Server": {
                        "x86_64": [
                            {
                                "file": "GPL",
                                "location": {
                                    "url": "https://cdn.example.com/GPL",
                                    "size": 18092,
                                    "checksum": "sha256:" + "a" * 64,
                                    "local_path": "Server/x86_64/os/GPL",
                                },
                            }
                        ]
                    }
                },
            },
        }

        # Load v2.0
        ef = ExtraFiles()
        ef.deserialize(data_v2)

        # Serialize as v1.2
        data_v1 = {}
        ef.serialize(data_v1, force_version=VERSION_1_2)

        assert data_v1["header"]["version"] == "1.2"
        entry = data_v1["payload"]["extra_files"]["Server"]["x86_64"][0]
        assert "checksums" in entry
        assert "size" in entry
        assert "location" not in entry
        # file should be the full local_path from location (v1.x format)
        assert entry["file"] == "Server/x86_64/os/GPL"
        assert entry["size"] == 18092
        assert entry["checksums"] == {"sha256": "a" * 64}

    def test_dump_for_tree_after_v20_deserialize(self):
        """Test dump_for_tree works after deserializing v2.0 data."""
        from io import StringIO
        import json

        data_v2 = {
            "header": {"type": "productmd.extra_files", "version": "2.0"},
            "payload": {
                "compose": {
                    "id": "Test-1.0-20240101.0",
                    "date": "20240101",
                    "type": "production",
                    "respin": 0,
                },
                "extra_files": {
                    "Server": {
                        "x86_64": [
                            {
                                "file": "GPL",
                                "location": {
                                    "url": "https://cdn.example.com/GPL",
                                    "size": 18092,
                                    "checksum": "sha256:" + "a" * 64,
                                    "local_path": "Server/x86_64/os/GPL",
                                },
                            }
                        ]
                    }
                },
            },
        }

        ef = ExtraFiles()
        ef.deserialize(data_v2)

        # dump_for_tree should work with v1.x-compatible internal format
        out = StringIO()
        ef.dump_for_tree(out, "Server", "x86_64", "Server/x86_64/os")

        tree_data = json.loads(out.getvalue())
        assert tree_data["data"][0]["file"] == "GPL"
        assert tree_data["data"][0]["size"] == 18092
        assert tree_data["data"][0]["checksums"] == {"sha256": "a" * 64}
