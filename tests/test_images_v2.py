# -*- coding: utf-8 -*-

"""Tests for v2.0 Image support with Location objects."""

import pytest

from productmd.images import Images, Image
from productmd.location import Location
from productmd.version import VERSION_1_2, VERSION_2_0, OUTPUT_FORMAT_VERSION


def _create_images():
    """Create an Images container."""
    images = Images()
    images.compose.id = "Test-1.0-20240101.0"
    images.compose.date = "20240101"
    images.compose.type = "production"
    images.compose.respin = 0
    return images


def _create_image(images):
    """Create a basic Image object."""
    image = Image(images)
    image.path = "Server/x86_64/iso/test.iso"
    image.mtime = 1704067200
    image.size = 2147483648
    image.volume_id = "Test-1.0"
    image.type = "dvd"
    image.format = "iso"
    image.arch = "x86_64"
    image.disc_number = 1
    image.disc_count = 1
    image.checksums = {"sha256": "a" * 64}
    image.implant_md5 = "b" * 32
    image.bootable = True
    image.subvariant = "Server"
    return image


class TestImageLocation:
    """Tests for Image.location property."""

    def test_location_property_creates_from_v12_fields(self):
        """Test that location property creates Location from v1.2 fields."""
        images = _create_images()
        image = _create_image(images)

        loc = image.location
        assert isinstance(loc, Location)
        assert loc.url == "Server/x86_64/iso/test.iso"
        assert loc.local_path == "Server/x86_64/iso/test.iso"
        assert loc.size == 2147483648
        assert loc.checksum == "sha256:" + "a" * 64

    def test_location_setter_updates_v12_fields(self):
        """Test that setting location updates v1.2 compatibility fields."""
        images = _create_images()
        image = _create_image(images)

        new_loc = Location(
            url="https://cdn.example.com/Server/x86_64/iso/new.iso",
            size=3000000000,
            checksum="sha256:" + "c" * 64,
            local_path="Server/x86_64/iso/new.iso",
        )
        image.location = new_loc

        assert image.path == "Server/x86_64/iso/new.iso"
        assert image.size == 3000000000
        assert image.checksums == {"sha256": "c" * 64}

    def test_is_remote_property(self):
        """Test is_remote property."""
        images = _create_images()
        image = _create_image(images)

        # Local path - not remote
        assert not image.is_remote

        # Set remote location
        image.location = Location(
            url="https://cdn.example.com/test.iso",
            size=1000,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/iso/test.iso",
        )
        assert image.is_remote


class TestImageSerialization:
    """Tests for Image serialization in v1.2 and v2.0 formats."""

    @pytest.mark.parametrize(
        "version, present_keys, absent_keys",
        [
            (VERSION_1_2, ["path", "size", "checksums"], ["location"]),
            (VERSION_2_0, ["location"], ["path", "size", "checksums"]),
        ],
    )
    def test_serialize_format(self, version, present_keys, absent_keys):
        """Test serialization produces correct keys for each format version."""
        images = _create_images()
        image = _create_image(images)

        result = []
        image.serialize(result, force_version=version)

        assert len(result) == 1
        data = result[0]
        for key in present_keys:
            assert key in data, "expected key '%s' in %s output" % (key, version)
        for key in absent_keys:
            assert key not in data, "unexpected key '%s' in %s output" % (key, version)

    def test_serialize_v12_values(self):
        """Test v1.2 serialization field values."""
        images = _create_images()
        image = _create_image(images)

        result = []
        image.serialize(result, force_version=VERSION_1_2)

        data = result[0]
        assert data["path"] == "Server/x86_64/iso/test.iso"

    def test_serialize_v20_values(self):
        """Test v2.0 serialization location values."""
        images = _create_images()
        image = _create_image(images)

        result = []
        image.serialize(result, force_version=VERSION_2_0)

        loc = result[0]["location"]
        assert loc["local_path"] == "Server/x86_64/iso/test.iso"
        assert loc["size"] == 2147483648
        assert loc["checksum"] == "sha256:" + "a" * 64

    def test_serialize_v20_with_remote_url(self):
        """Test serialization in v2.0 format with remote URL."""
        images = _create_images()
        image = _create_image(images)

        image.location = Location(
            url="https://cdn.example.com/Server/x86_64/iso/test.iso",
            size=2147483648,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/iso/test.iso",
        )

        result = []
        image.serialize(result, force_version=VERSION_2_0)

        loc = result[0]["location"]
        assert loc["url"] == "https://cdn.example.com/Server/x86_64/iso/test.iso"

    def test_deserialize_v12_format(self):
        """Test deserialization from v1.2 format."""
        images = _create_images()
        image = Image(images)

        data = {
            "path": "Server/x86_64/iso/test.iso",
            "mtime": 1704067200,
            "size": 2147483648,
            "volume_id": "Test-1.0",
            "type": "dvd",
            "format": "iso",
            "arch": "x86_64",
            "disc_number": 1,
            "disc_count": 1,
            "checksums": {"sha256": "a" * 64},
            "implant_md5": "b" * 32,
            "bootable": True,
            "subvariant": "Server",
        }
        image.deserialize(data)

        assert image.path == "Server/x86_64/iso/test.iso"
        assert image.size == 2147483648
        assert image._location is None

    def test_deserialize_v20_format(self):
        """Test deserialization from v2.0 format."""
        images = _create_images()
        images.header.version = "2.0"
        image = Image(images)

        data = {
            "location": {
                "url": "https://cdn.example.com/Server/x86_64/iso/test.iso",
                "size": 2147483648,
                "checksum": "sha256:" + "a" * 64,
                "local_path": "Server/x86_64/iso/test.iso",
            },
            "mtime": 1704067200,
            "volume_id": "Test-1.0",
            "type": "dvd",
            "format": "iso",
            "arch": "x86_64",
            "disc_number": 1,
            "disc_count": 1,
            "implant_md5": "b" * 32,
            "bootable": True,
            "subvariant": "Server",
        }
        image.deserialize(data)

        # Check v2.0 fields
        assert image._location is not None
        assert image._location.url == "https://cdn.example.com/Server/x86_64/iso/test.iso"
        assert image.is_remote

        # Check v1.2 compatibility fields
        assert image.path == "Server/x86_64/iso/test.iso"
        assert image.size == 2147483648
        assert image.checksums == {"sha256": "a" * 64}


class TestImagesContainerVersioning:
    """Tests for Images container version handling."""

    def _create_images_with_image(self):
        """Create an Images container with one image."""
        images = _create_images()
        image = _create_image(images)
        images.add("Server", "x86_64", image)
        return images

    def test_output_version_default(self):
        """Test output_version defaults to OUTPUT_FORMAT_VERSION."""
        images = Images()
        assert images.output_version == OUTPUT_FORMAT_VERSION

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
        images = Images()
        images.output_version = value
        assert images.output_version == expected

    @pytest.mark.parametrize(
        "version, present_key, absent_key, header_version",
        [
            (VERSION_1_2, "path", "location", "1.2"),
            (VERSION_2_0, "location", "path", "2.0"),
        ],
    )
    def test_serialize_container(self, version, present_key, absent_key, header_version):
        """Test Images container serialization in v1.2 and v2.0 formats."""
        images = self._create_images_with_image()

        data = {}
        images.serialize(data, force_version=version)

        assert "header" in data
        assert "payload" in data
        assert "images" in data["payload"]
        assert data["header"]["version"] == header_version

        image_data = data["payload"]["images"]["Server"]["x86_64"][0]
        assert present_key in image_data
        assert absent_key not in image_data


class TestRoundTrip:
    """Tests for round-trip serialization/deserialization."""

    def test_v12_roundtrip(self):
        """Test v1.2 format round-trip."""
        images = _create_images()
        image = _create_image(images)
        images.add("Server", "x86_64", image)

        # Serialize
        data = {}
        images.serialize(data, force_version=VERSION_1_2)

        # Deserialize into new object
        images2 = Images()
        images2.deserialize(data)

        # Check
        image2 = list(images2.images["Server"]["x86_64"])[0]
        assert image2.path == image.path
        assert image2.size == image.size
        assert image2.checksums == image.checksums

    def test_v20_roundtrip(self):
        """Test v2.0 format round-trip."""
        images = _create_images()
        image = _create_image(images)

        # Set remote location
        image.location = Location(
            url="https://cdn.example.com/Server/x86_64/iso/test.iso",
            size=2147483648,
            checksum="sha256:" + "a" * 64,
            local_path="Server/x86_64/iso/test.iso",
        )
        images.add("Server", "x86_64", image)

        # Serialize as v2.0
        data = {}
        images.serialize(data, force_version=VERSION_2_0)

        # Verify header version is 2.0
        assert data["header"]["version"] == "2.0"

        # Deserialize into new object
        images2 = Images()
        images2.deserialize(data)

        # Verify header version was read correctly
        assert images2.header.version_tuple == (2, 0)

        # Check
        image2 = list(images2.images["Server"]["x86_64"])[0]
        assert image2.path == "Server/x86_64/iso/test.iso"
        assert image2.size == 2147483648
        assert image2.is_remote
        assert image2._location.url == "https://cdn.example.com/Server/x86_64/iso/test.iso"
