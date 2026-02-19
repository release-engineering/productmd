"""Tests for v2.0 Modules support with Location objects."""

import pytest

from productmd.modules import Modules
from productmd.location import Location
from productmd.version import VERSION_1_2, VERSION_2_0, OUTPUT_FORMAT_VERSION


def _create_modules():
    """Create a Modules container with compose metadata."""
    modules = Modules()
    modules.compose.id = "Test-1.0-20240101.0"
    modules.compose.date = "20240101"
    modules.compose.type = "production"
    modules.compose.respin = 0
    return modules


def _add_sample_module(modules):
    """Add a sample module via the add() method."""
    modules.add(
        variant="Server",
        arch="x86_64",
        uid="testmod:1.0:20240101000000:abcd1234",
        koji_tag="module-tag-12345",
        modulemd_path="Server/x86_64/os/repodata/modules.yaml.gz",
        category="binary",
        rpms=["pkg1-0:1.0-1.fc41.x86_64.rpm", "pkg2-0:2.0-1.fc41.x86_64.rpm"],
    )
    return modules


def _make_v1_data():
    """Create a v1.x format data dict."""
    return {
        "header": {"type": "productmd.modules", "version": "1.2"},
        "payload": {
            "compose": {
                "id": "Test-1.0-20240101.0",
                "date": "20240101",
                "type": "production",
                "respin": 0,
            },
            "modules": {
                "Server": {
                    "x86_64": {
                        "testmod:1.0:20240101000000:abcd1234": {
                            "metadata": {
                                "uid": "testmod:1.0:20240101000000:abcd1234",
                                "name": "testmod",
                                "stream": "1.0",
                                "version": "20240101000000",
                                "context": "abcd1234",
                                "koji_tag": "module-tag-12345",
                            },
                            "modulemd_path": {
                                "binary": "Server/x86_64/os/repodata/modules.yaml.gz",
                            },
                            "rpms": ["pkg1-0:1.0-1.fc41.x86_64.rpm"],
                        }
                    }
                }
            },
        },
    }


def _make_v2_data():
    """Create a v2.0 format data dict."""
    return {
        "header": {"type": "productmd.modules", "version": "2.0"},
        "payload": {
            "compose": {
                "id": "Test-1.0-20240101.0",
                "date": "20240101",
                "type": "production",
                "respin": 0,
            },
            "modules": {
                "Server": {
                    "x86_64": {
                        "testmod:1.0:20240101000000:abcd1234": {
                            "name": "testmod",
                            "stream": "1.0",
                            "version": "20240101000000",
                            "context": "abcd1234",
                            "arch": "x86_64",
                            "location": {
                                "url": "https://cdn.example.com/Server/x86_64/os/repodata/modules.yaml.gz",
                                "size": 123456,
                                "checksum": "sha256:" + "a" * 64,
                                "local_path": "Server/x86_64/os/repodata/modules.yaml.gz",
                            },
                            "rpms": ["pkg1-0:1.0-1.fc41.x86_64.rpm"],
                        }
                    }
                }
            },
        },
    }


class TestModulesVersioning:
    """Tests for Modules container version handling via VersionedMetadataMixin."""

    def test_output_version_default(self):
        """Test output_version defaults to OUTPUT_FORMAT_VERSION."""
        modules = Modules()
        assert modules.output_version == OUTPUT_FORMAT_VERSION

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
        modules = Modules()
        modules.output_version = value
        assert modules.output_version == expected


class TestModulesSerialization:
    """Tests for Modules serialization in v1.2 and v2.0 formats."""

    @pytest.mark.parametrize(
        "version, present_key, absent_key",
        [
            (VERSION_1_2, "metadata", "arch"),
            (VERSION_2_0, "arch", "metadata"),
        ],
    )
    def test_serialize_format_keys(self, version, present_key, absent_key):
        """Test serialization produces correct keys for each format version."""
        modules = _create_modules()
        _add_sample_module(modules)

        data = {}
        modules.serialize(data, force_version=version)

        entry = data["payload"]["modules"]["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]
        assert present_key in entry, f"expected '{present_key}' in {version} output"
        assert absent_key not in entry, f"unexpected '{absent_key}' in {version} output"

    def test_serialize_v12_values(self):
        """Test v1.2 serialization produces correct field values."""
        modules = _create_modules()
        _add_sample_module(modules)

        data = {}
        modules.serialize(data, force_version=VERSION_1_2)

        assert data["header"]["version"] == "1.2"

        entry = data["payload"]["modules"]["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]
        assert entry["metadata"]["uid"] == "testmod:1.0:20240101000000:abcd1234"
        assert entry["metadata"]["name"] == "testmod"
        assert entry["metadata"]["stream"] == "1.0"
        assert entry["metadata"]["version"] == "20240101000000"
        assert entry["metadata"]["context"] == "abcd1234"
        assert entry["metadata"]["koji_tag"] == "module-tag-12345"
        assert entry["modulemd_path"]["binary"] == "Server/x86_64/os/repodata/modules.yaml.gz"
        assert "pkg1-0:1.0-1.fc41.x86_64.rpm" in entry["rpms"]

    def test_serialize_v20_values(self):
        """Test v2.0 serialization produces flattened fields with location."""
        modules = _create_modules()
        _add_sample_module(modules)

        data = {}
        modules.serialize(data, force_version=VERSION_2_0)

        assert data["header"]["version"] == "2.0"

        entry = data["payload"]["modules"]["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]
        assert entry["name"] == "testmod"
        assert entry["stream"] == "1.0"
        assert entry["version"] == "20240101000000"
        assert entry["context"] == "abcd1234"
        assert entry["arch"] == "x86_64"
        assert "location" in entry
        assert "metadata" not in entry
        assert "modulemd_path" not in entry
        assert "koji_tag" not in entry

        loc = entry["location"]
        assert loc["local_path"] == "Server/x86_64/os/repodata/modules.yaml.gz"
        # url defaults to path when no explicit location is set
        assert loc["url"] == "Server/x86_64/os/repodata/modules.yaml.gz"

        assert "pkg1-0:1.0-1.fc41.x86_64.rpm" in entry["rpms"]

    def test_serialize_v20_with_explicit_location(self):
        """Test v2.0 serialization with an explicitly set Location."""
        modules = _create_modules()
        _add_sample_module(modules)

        loc = Location(
            url="https://cdn.example.com/Server/x86_64/os/repodata/modules.yaml.gz",
            size=123456,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/repodata/modules.yaml.gz",
        )
        modules.modules["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]["_location"] = loc

        data = {}
        modules.serialize(data, force_version=VERSION_2_0)

        entry = data["payload"]["modules"]["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]
        assert entry["location"]["url"] == "https://cdn.example.com/Server/x86_64/os/repodata/modules.yaml.gz"
        assert entry["location"]["size"] == 123456
        assert entry["location"]["checksum"] == "sha256:" + "a" * 64

    def test_deserialize_v12_format(self):
        """Test deserialization from v1.2 format."""
        data = _make_v1_data()

        modules = Modules()
        modules.deserialize(data)

        entry = modules.modules["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]
        assert entry["metadata"]["name"] == "testmod"
        assert entry["metadata"]["koji_tag"] == "module-tag-12345"
        assert entry["modulemd_path"]["binary"] == "Server/x86_64/os/repodata/modules.yaml.gz"
        assert "pkg1-0:1.0-1.fc41.x86_64.rpm" in entry["rpms"]
        # v1.x data should not have _location
        assert "_location" not in entry

    def test_deserialize_v20_format(self):
        """Test deserialization from v2.0 format."""
        data = _make_v2_data()

        modules = Modules()
        modules.deserialize(data)

        entry = modules.modules["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]

        # v1.x compatibility fields populated from v2.0 data
        assert entry["metadata"]["uid"] == "testmod:1.0:20240101000000:abcd1234"
        assert entry["metadata"]["name"] == "testmod"
        assert entry["metadata"]["stream"] == "1.0"
        assert entry["metadata"]["version"] == "20240101000000"
        assert entry["metadata"]["context"] == "abcd1234"
        assert entry["metadata"]["koji_tag"] == ""  # not present in v2.0, defaults to empty
        assert entry["modulemd_path"]["binary"] == "Server/x86_64/os/repodata/modules.yaml.gz"
        assert "pkg1-0:1.0-1.fc41.x86_64.rpm" in entry["rpms"]

        # Location preserved for round-trip
        assert entry["_location"] is not None
        assert isinstance(entry["_location"], Location)
        assert entry["_location"].url == "https://cdn.example.com/Server/x86_64/os/repodata/modules.yaml.gz"
        assert entry["_location"].size == 123456

    @pytest.mark.parametrize(
        "version, header_version",
        [
            (VERSION_1_2, "1.2"),
            (VERSION_2_0, "2.0"),
        ],
    )
    def test_header_version_matches_output(self, version, header_version):
        """Test that the serialized header version matches force_version."""
        modules = _create_modules()
        _add_sample_module(modules)

        data = {}
        modules.serialize(data, force_version=version)

        assert data["header"]["version"] == header_version

    def test_deserialize_v20_preserves_header_version(self):
        """Test that deserializing v2.0 preserves the header version."""
        data = _make_v2_data()

        modules = Modules()
        modules.deserialize(data)

        assert modules.header.version_tuple == (2, 0)

    def test_deserialize_v12_preserves_version(self):
        """Test that deserializing v1.2 preserves the file version."""
        data = _make_v1_data()

        modules = Modules()
        modules.deserialize(data)

        # Version is preserved for round-trip fidelity
        assert modules.output_version == (1, 2)


class TestModulesRoundTrip:
    """Tests for round-trip serialization/deserialization."""

    def test_v12_roundtrip(self):
        """Test v1.2 format round-trip preserves data."""
        modules = _create_modules()
        _add_sample_module(modules)

        # Serialize as v1.2
        data = {}
        modules.serialize(data, force_version=VERSION_1_2)

        # Deserialize into new object
        modules2 = Modules()
        modules2.deserialize(data)

        entry = modules2.modules["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]
        assert entry["metadata"]["name"] == "testmod"
        assert entry["metadata"]["koji_tag"] == "module-tag-12345"
        assert entry["modulemd_path"]["binary"] == "Server/x86_64/os/repodata/modules.yaml.gz"

    def test_v20_roundtrip(self):
        """Test v2.0 format round-trip preserves data including location."""
        modules = _create_modules()
        _add_sample_module(modules)

        # Attach a remote Location
        loc = Location(
            url="https://cdn.example.com/Server/x86_64/os/repodata/modules.yaml.gz",
            size=123456,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/repodata/modules.yaml.gz",
        )
        modules.modules["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]["_location"] = loc

        # Serialize as v2.0
        data = {}
        modules.serialize(data, force_version=VERSION_2_0)
        assert data["header"]["version"] == "2.0"

        # Deserialize into new object
        modules2 = Modules()
        modules2.deserialize(data)
        assert modules2.header.version_tuple == (2, 0)

        # Verify v1.x compatibility fields
        entry = modules2.modules["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]
        assert entry["metadata"]["name"] == "testmod"
        assert entry["modulemd_path"]["binary"] == "Server/x86_64/os/repodata/modules.yaml.gz"

        # Verify Location round-trip
        assert entry["_location"].url == "https://cdn.example.com/Server/x86_64/os/repodata/modules.yaml.gz"
        assert entry["_location"].size == 123456
        assert entry["_location"].checksum == "sha256:" + "a" * 64

    def test_v20_roundtrip_identity(self):
        """Test v2.0 serialize-deserialize-serialize produces identical output."""
        modules = _create_modules()
        _add_sample_module(modules)

        loc = Location(
            url="https://cdn.example.com/Server/x86_64/os/repodata/modules.yaml.gz",
            size=123456,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os/repodata/modules.yaml.gz",
        )
        modules.modules["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]["_location"] = loc

        # First serialize
        data1 = {}
        modules.serialize(data1, force_version=VERSION_2_0)

        # Deserialize and re-serialize
        modules2 = Modules()
        modules2.deserialize(data1)
        data2 = {}
        modules2.serialize(data2, force_version=VERSION_2_0)

        # Compare payload
        assert data1["payload"]["modules"] == data2["payload"]["modules"]
        assert data1["header"]["version"] == data2["header"]["version"]

    def test_v20_to_v12_downgrade(self):
        """Test deserializing v2.0 and re-serializing as v1.2."""
        data_v2 = _make_v2_data()

        # Load v2.0
        modules = Modules()
        modules.deserialize(data_v2)

        # Serialize as v1.2
        data_v1 = {}
        modules.serialize(data_v1, force_version=VERSION_1_2)

        assert data_v1["header"]["version"] == "1.2"
        entry = data_v1["payload"]["modules"]["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]
        assert "metadata" in entry
        assert "modulemd_path" in entry
        assert "location" not in entry
        assert "arch" not in entry
        assert entry["metadata"]["name"] == "testmod"
        assert entry["modulemd_path"]["binary"] == "Server/x86_64/os/repodata/modules.yaml.gz"

    def test_v12_to_v20_upgrade(self):
        """Test deserializing v1.2 and re-serializing as v2.0."""
        data_v1 = _make_v1_data()

        # Load v1.2
        modules = Modules()
        modules.deserialize(data_v1)

        # Serialize as v2.0
        data_v2 = {}
        modules.serialize(data_v2, force_version=VERSION_2_0)

        assert data_v2["header"]["version"] == "2.0"
        entry = data_v2["payload"]["modules"]["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]
        assert entry["name"] == "testmod"
        assert entry["stream"] == "1.0"
        assert entry["arch"] == "x86_64"
        assert "location" in entry
        assert "metadata" not in entry
        assert entry["location"]["local_path"] == "Server/x86_64/os/repodata/modules.yaml.gz"

    def test_multiple_arches(self):
        """Test handling of modules across multiple architectures."""
        modules = _create_modules()

        # Add same module to two arches
        modules.add(
            variant="Server",
            arch="x86_64",
            uid="testmod:1.0:20240101000000:abcd1234",
            koji_tag="module-tag-12345",
            modulemd_path="Server/x86_64/os/repodata/modules.yaml.gz",
            category="binary",
            rpms=["pkg1-0:1.0-1.fc41.x86_64.rpm"],
        )
        modules.add(
            variant="Server",
            arch="aarch64",
            uid="testmod:1.0:20240101000000:abcd1234",
            koji_tag="module-tag-12345",
            modulemd_path="Server/aarch64/os/repodata/modules.yaml.gz",
            category="binary",
            rpms=["pkg1-0:1.0-1.fc41.aarch64.rpm"],
        )

        # Serialize as v2.0
        data = {}
        modules.serialize(data, force_version=VERSION_2_0)

        x86_entry = data["payload"]["modules"]["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]
        arm_entry = data["payload"]["modules"]["Server"]["aarch64"]["testmod:1.0:20240101000000:abcd1234"]

        assert x86_entry["arch"] == "x86_64"
        assert arm_entry["arch"] == "aarch64"
        assert x86_entry["location"]["local_path"] == "Server/x86_64/os/repodata/modules.yaml.gz"
        assert arm_entry["location"]["local_path"] == "Server/aarch64/os/repodata/modules.yaml.gz"

    def test_v10_modulemd_path_string(self):
        """Test handling of v1.0 format where modulemd_path is a plain string."""
        modules = _create_modules()
        modules.modules = {
            "Server": {
                "x86_64": {
                    "testmod:1.0:20240101000000:abcd1234": {
                        "metadata": {
                            "uid": "testmod:1.0:20240101000000:abcd1234",
                            "name": "testmod",
                            "stream": "1.0",
                            "version": "20240101000000",
                            "context": "abcd1234",
                            "koji_tag": "module-tag-12345",
                        },
                        "modulemd_path": "Server/x86_64/os/repodata/modules.yaml.gz",
                        "rpms": [],
                    }
                }
            }
        }

        # Serialize as v2.0 — should handle string modulemd_path
        data = {}
        modules.serialize(data, force_version=VERSION_2_0)

        entry = data["payload"]["modules"]["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]
        assert entry["location"]["local_path"] == "Server/x86_64/os/repodata/modules.yaml.gz"

        # Serialize as v1.2 — should preserve string format
        data_v1 = {}
        modules.serialize(data_v1, force_version=VERSION_1_2)

        entry_v1 = data_v1["payload"]["modules"]["Server"]["x86_64"]["testmod:1.0:20240101000000:abcd1234"]
        assert entry_v1["modulemd_path"] == "Server/x86_64/os/repodata/modules.yaml.gz"
