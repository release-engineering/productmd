"""Tests for v2.0 ComposeInfo support with Location objects in VariantPaths."""

import pytest

from productmd.composeinfo import ComposeInfo, Variant
from productmd.location import Location
from productmd.version import VERSION_1_2, VERSION_2_0, OUTPUT_FORMAT_VERSION


def _create_composeinfo():
    """Create a ComposeInfo with basic release and compose metadata."""
    ci = ComposeInfo()
    ci.release.name = "Fedora"
    ci.release.short = "Fedora"
    ci.release.version = "41"
    ci.release.type = "ga"

    ci.compose.id = "Fedora-41-20260204.0"
    ci.compose.type = "production"
    ci.compose.date = "20260204"
    ci.compose.respin = 0

    return ci


def _add_server_variant(ci):
    """Add a Server variant with paths to the ComposeInfo."""
    variant = Variant(ci)
    variant.id = "Server"
    variant.uid = "Server"
    variant.name = "Fedora Server"
    variant.type = "variant"
    variant.arches = set(["x86_64", "aarch64"])

    variant.paths.os_tree = {
        "x86_64": "Server/x86_64/os",
        "aarch64": "Server/aarch64/os",
    }
    variant.paths.packages = {
        "x86_64": "Server/x86_64/os/Packages",
        "aarch64": "Server/aarch64/os/Packages",
    }

    ci.variants.add(variant)
    return ci


class TestComposeInfoVersioning:
    """Tests for ComposeInfo version handling via VersionedMetadataMixin."""

    def test_output_version_default(self):
        """Test output_version defaults to OUTPUT_FORMAT_VERSION."""
        ci = ComposeInfo()
        assert ci.output_version == OUTPUT_FORMAT_VERSION

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
        ci = ComposeInfo()
        ci.output_version = value
        assert ci.output_version == expected


class TestVariantPathsSerialization:
    """Tests for VariantPaths serialization in v1.2 and v2.0 formats."""

    @pytest.mark.parametrize("version", [VERSION_1_2, VERSION_2_0])
    def test_serialize_has_paths(self, version):
        """Test that both formats include variant paths."""
        ci = _create_composeinfo()
        _add_server_variant(ci)

        data = {}
        ci.serialize(data, force_version=version)

        server = data["payload"]["variants"]["Server"]
        assert "paths" in server
        assert "os_tree" in server["paths"]
        assert "x86_64" in server["paths"]["os_tree"]

    def test_serialize_v12_paths_are_strings(self):
        """Test v1.2 serialization produces plain path strings."""
        ci = _create_composeinfo()
        _add_server_variant(ci)

        data = {}
        ci.serialize(data, force_version=VERSION_1_2)

        assert data["header"]["version"] == "1.2"

        os_tree = data["payload"]["variants"]["Server"]["paths"]["os_tree"]["x86_64"]
        assert isinstance(os_tree, str)
        assert os_tree == "Server/x86_64/os"

        packages = data["payload"]["variants"]["Server"]["paths"]["packages"]["x86_64"]
        assert isinstance(packages, str)
        assert packages == "Server/x86_64/os/Packages"

    def test_serialize_v20_paths_are_locations(self):
        """Test v2.0 serialization produces Location objects."""
        ci = _create_composeinfo()
        _add_server_variant(ci)

        data = {}
        ci.serialize(data, force_version=VERSION_2_0)

        assert data["header"]["version"] == "2.0"

        os_tree = data["payload"]["variants"]["Server"]["paths"]["os_tree"]["x86_64"]
        assert isinstance(os_tree, dict)
        assert "url" in os_tree
        assert "local_path" in os_tree
        assert os_tree["local_path"] == "Server/x86_64/os"

    def test_serialize_v20_with_explicit_location(self):
        """Test v2.0 serialization with explicitly set Location objects."""
        ci = _create_composeinfo()
        _add_server_variant(ci)

        # Attach Location objects to the variant paths
        server = ci.variants["Server"]
        loc = Location(
            url="https://cdn.example.com/Server/x86_64/os/",
            size=2847,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os",
        )
        server.paths._locations.setdefault("os_tree", {})["x86_64"] = loc

        data = {}
        ci.serialize(data, force_version=VERSION_2_0)

        os_tree = data["payload"]["variants"]["Server"]["paths"]["os_tree"]["x86_64"]
        assert os_tree["url"] == "https://cdn.example.com/Server/x86_64/os/"
        assert os_tree["size"] == 2847
        assert os_tree["checksum"] == "sha256:" + "a" * 64
        assert os_tree["local_path"] == "Server/x86_64/os"

    def test_deserialize_v12_format(self):
        """Test deserialization from v1.2 format."""
        data = {
            "header": {"type": "productmd.composeinfo", "version": "1.2"},
            "payload": {
                "compose": {
                    "id": "Fedora-41-20260204.0",
                    "date": "20260204",
                    "type": "production",
                    "respin": 0,
                },
                "release": {
                    "name": "Fedora",
                    "short": "Fedora",
                    "version": "41",
                    "type": "ga",
                },
                "variants": {
                    "Server": {
                        "id": "Server",
                        "uid": "Server",
                        "name": "Fedora Server",
                        "type": "variant",
                        "arches": ["x86_64"],
                        "paths": {
                            "os_tree": {"x86_64": "Server/x86_64/os"},
                            "packages": {"x86_64": "Server/x86_64/os/Packages"},
                        },
                    }
                },
            },
        }

        ci = ComposeInfo()
        ci.deserialize(data)

        server = ci.variants["Server"]
        assert server.paths.os_tree == {"x86_64": "Server/x86_64/os"}
        assert server.paths.packages == {"x86_64": "Server/x86_64/os/Packages"}
        # v1.x data should not have locations
        assert server.paths._locations == {}

    def test_deserialize_v20_format(self):
        """Test deserialization from v2.0 format."""
        data = {
            "header": {"type": "productmd.composeinfo", "version": "2.0"},
            "payload": {
                "compose": {
                    "id": "Fedora-41-20260204.0",
                    "date": "20260204",
                    "type": "production",
                    "respin": 0,
                },
                "release": {
                    "name": "Fedora",
                    "short": "Fedora",
                    "version": "41",
                    "type": "ga",
                },
                "variants": {
                    "Server": {
                        "id": "Server",
                        "uid": "Server",
                        "name": "Fedora Server",
                        "type": "variant",
                        "arches": ["x86_64"],
                        "paths": {
                            "os_tree": {
                                "x86_64": {
                                    "url": "https://cdn.example.com/Server/x86_64/os/",
                                    "size": 2847,
                                    "checksum": "sha256:" + "a" * 64,
                                    "local_path": "Server/x86_64/os",
                                }
                            },
                        },
                    }
                },
            },
        }

        ci = ComposeInfo()
        ci.deserialize(data)

        server = ci.variants["Server"]

        # v1.x compatibility: paths are still plain strings
        assert server.paths.os_tree == {"x86_64": "Server/x86_64/os"}

        # Location preserved for round-trip
        assert "os_tree" in server.paths._locations
        assert "x86_64" in server.paths._locations["os_tree"]
        loc = server.paths._locations["os_tree"]["x86_64"]
        assert isinstance(loc, Location)
        assert loc.url == "https://cdn.example.com/Server/x86_64/os/"
        assert loc.size == 2847

    @pytest.mark.parametrize(
        "version, header_version",
        [
            (VERSION_1_2, "1.2"),
            (VERSION_2_0, "2.0"),
        ],
    )
    def test_header_version_matches_output(self, version, header_version):
        """Test that the serialized header version matches force_version."""
        ci = _create_composeinfo()
        _add_server_variant(ci)

        data = {}
        ci.serialize(data, force_version=version)

        assert data["header"]["version"] == header_version


class TestComposeInfoRoundTrip:
    """Tests for round-trip serialization/deserialization."""

    def test_v12_roundtrip(self):
        """Test v1.2 format round-trip preserves data."""
        ci = _create_composeinfo()
        _add_server_variant(ci)

        # Serialize as v1.2
        data = {}
        ci.serialize(data, force_version=VERSION_1_2)

        # Deserialize into new object
        ci2 = ComposeInfo()
        ci2.deserialize(data)

        # Verify variant paths preserved
        server = ci2.variants["Server"]
        assert server.paths.os_tree == {"x86_64": "Server/x86_64/os", "aarch64": "Server/aarch64/os"}
        assert server.paths.packages == {"x86_64": "Server/x86_64/os/Packages", "aarch64": "Server/aarch64/os/Packages"}

    def test_v20_roundtrip(self):
        """Test v2.0 format round-trip preserves data including locations."""
        ci = _create_composeinfo()
        _add_server_variant(ci)

        # Attach Location to os_tree
        server = ci.variants["Server"]
        loc = Location(
            url="https://cdn.example.com/Server/x86_64/os/",
            size=2847,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/os",
        )
        server.paths._locations.setdefault("os_tree", {})["x86_64"] = loc

        # Serialize as v2.0
        data = {}
        ci.serialize(data, force_version=VERSION_2_0)
        assert data["header"]["version"] == "2.0"

        # Deserialize into new object
        ci2 = ComposeInfo()
        ci2.deserialize(data)
        assert ci2.header.version_tuple == (2, 0)

        # Verify v1.x compatibility
        server2 = ci2.variants["Server"]
        assert server2.paths.os_tree["x86_64"] == "Server/x86_64/os"

        # Verify Location round-trip
        loc2 = server2.paths._locations["os_tree"]["x86_64"]
        assert loc2.url == "https://cdn.example.com/Server/x86_64/os/"
        assert loc2.size == 2847

    def test_v20_roundtrip_identity(self):
        """Test v2.0 serialize-deserialize-serialize produces identical output."""
        ci = _create_composeinfo()
        _add_server_variant(ci)

        server = ci.variants["Server"]
        for arch in ["x86_64", "aarch64"]:
            loc = Location(
                url=f"https://cdn.example.com/Server/{arch}/os/",
                size=2847,
                checksum="sha256:" + "a" * 64,
                local_path=f"Server/{arch}/os",
            )
            server.paths._locations.setdefault("os_tree", {})[arch] = loc

        # First serialize
        data1 = {}
        ci.serialize(data1, force_version=VERSION_2_0)

        # Deserialize and re-serialize
        ci2 = ComposeInfo()
        ci2.deserialize(data1)
        data2 = {}
        ci2.serialize(data2, force_version=VERSION_2_0)

        # Compare variant paths
        assert data1["payload"]["variants"] == data2["payload"]["variants"]
        assert data1["header"]["version"] == data2["header"]["version"]

    def test_v20_to_v12_downgrade(self):
        """Test deserializing v2.0 and re-serializing as v1.2."""
        data_v2 = {
            "header": {"type": "productmd.composeinfo", "version": "2.0"},
            "payload": {
                "compose": {
                    "id": "Fedora-41-20260204.0",
                    "date": "20260204",
                    "type": "production",
                    "respin": 0,
                },
                "release": {
                    "name": "Fedora",
                    "short": "Fedora",
                    "version": "41",
                    "type": "ga",
                },
                "variants": {
                    "Server": {
                        "id": "Server",
                        "uid": "Server",
                        "name": "Fedora Server",
                        "type": "variant",
                        "arches": ["x86_64"],
                        "paths": {
                            "os_tree": {
                                "x86_64": {
                                    "url": "https://cdn.example.com/os/",
                                    "size": 2847,
                                    "checksum": "sha256:" + "a" * 64,
                                    "local_path": "Server/x86_64/os",
                                }
                            },
                        },
                    }
                },
            },
        }

        # Load v2.0
        ci = ComposeInfo()
        ci.deserialize(data_v2)

        # Serialize as v1.2
        data_v1 = {}
        ci.serialize(data_v1, force_version=VERSION_1_2)

        assert data_v1["header"]["version"] == "1.2"
        os_tree = data_v1["payload"]["variants"]["Server"]["paths"]["os_tree"]["x86_64"]
        # v1.2 paths should be plain strings
        assert isinstance(os_tree, str)
        assert os_tree == "Server/x86_64/os"

    def test_no_paths_variant(self):
        """Test that variants without paths work in both formats."""
        ci = _create_composeinfo()

        variant = Variant(ci)
        variant.id = "Server"
        variant.uid = "Server"
        variant.name = "Fedora Server"
        variant.type = "variant"
        variant.arches = set(["x86_64"])
        ci.variants.add(variant)

        # Should serialize fine with no paths
        for version in [VERSION_1_2, VERSION_2_0]:
            data = {}
            ci.serialize(data, force_version=version)
            assert "Server" in data["payload"]["variants"]
