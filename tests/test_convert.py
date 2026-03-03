"""Tests for conversion utilities (iter_all_locations, upgrade_to_v2, downgrade_to_v1)."""

import os

import pytest

from productmd.composeinfo import ComposeInfo, Variant
from productmd.convert import (
    LocationEntry,
    downgrade_to_v1,
    iter_all_locations,
    upgrade_to_v2,
)
from productmd.extra_files import ExtraFiles
from productmd.images import Image, Images
from productmd.location import Location
from productmd.modules import Modules
from productmd.rpms import Rpms
from productmd.version import VERSION_1_2, VERSION_2_0


# ---------------------------------------------------------------------------
# Helpers: create minimal metadata objects
# ---------------------------------------------------------------------------


def _make_image(parent, path, size, checksum_hex):
    img = Image(parent)
    img.path = path
    img.mtime = 1738627200
    img.size = size
    img.volume_id = "Test-1.0"
    img.type = "dvd"
    img.format = "iso"
    img.arch = "x86_64"
    img.disc_number = 1
    img.disc_count = 1
    img.checksums = {"sha256": checksum_hex}
    img.subvariant = ""
    return img


def _create_images():
    im = Images()
    im.header.version = "1.2"
    im.compose.id = "Test-1.0-20260204.0"
    im.compose.type = "production"
    im.compose.date = "20260204"
    im.compose.respin = 0
    im.output_version = VERSION_1_2

    boot = _make_image(im, "Server/x86_64/iso/boot.iso", 512000000, "a" * 64)
    boot.type = "boot"
    boot.subvariant = "Server"
    im.add("Server", "x86_64", boot)

    dvd = _make_image(im, "Server/x86_64/iso/dvd.iso", 2465792000, "b" * 64)
    dvd.type = "dvd"
    dvd.subvariant = "Server"
    im.add("Server", "x86_64", dvd)
    return im


def _create_rpms():
    rpms = Rpms()
    rpms.header.version = "1.2"
    rpms.compose.id = "Test-1.0-20260204.0"
    rpms.compose.type = "production"
    rpms.compose.date = "20260204"
    rpms.compose.respin = 0

    rpms.add(
        variant="Server",
        arch="x86_64",
        nevra="bash-0:5.2.26-3.fc41.x86_64",
        path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
        sigkey="a15b79cc",
        srpm_nevra="bash-0:5.2.26-3.fc41.src",
        category="binary",
    )
    return rpms


def _create_extra_files():
    ef = ExtraFiles()
    ef.header.version = "1.2"
    ef.compose.id = "Test-1.0-20260204.0"
    ef.compose.type = "production"
    ef.compose.date = "20260204"
    ef.compose.respin = 0

    ef.add(
        variant="Server",
        arch="x86_64",
        path="Server/x86_64/os/GPL",
        size=18092,
        checksums={"sha256": "c" * 64},
    )
    return ef


def _create_modules():
    modules = Modules()
    modules.header.version = "1.2"
    modules.compose.id = "Test-1.0-20260204.0"
    modules.compose.type = "production"
    modules.compose.date = "20260204"
    modules.compose.respin = 0

    modules.add(
        variant="Server",
        arch="x86_64",
        uid="nodejs:20:4120250101112233:f41",
        koji_tag="module-tag-12345",
        modulemd_path="Server/x86_64/os/repodata/modules.yaml.gz",
        category="binary",
        rpms=["nodejs-1:20.10.0-1.fc41.x86_64.rpm"],
    )
    return modules


def _create_composeinfo():
    ci = ComposeInfo()
    ci.release.name = "Fedora"
    ci.release.short = "Fedora"
    ci.release.version = "41"
    ci.release.type = "ga"
    ci.compose.id = "Fedora-41-20260204.0"
    ci.compose.type = "production"
    ci.compose.date = "20260204"
    ci.compose.respin = 0

    variant = Variant(ci)
    variant.id = "Server"
    variant.uid = "Server"
    variant.name = "Fedora Server"
    variant.type = "variant"
    variant.arches = set(["x86_64"])
    variant.paths.os_tree = {"x86_64": "Server/x86_64/os"}
    variant.paths.packages = {"x86_64": "Server/x86_64/os/Packages"}
    ci.variants.add(variant)
    return ci


def _create_images_v2():
    """Create Images with explicit Location objects (v2.0 data)."""
    im = _create_images()
    for variant in im.images:
        for arch in im.images[variant]:
            for image in im.images[variant][arch]:
                loc = Location(
                    url=f"https://cdn.example.com/{image.path}",
                    size=image.size,
                    checksum=f"sha256:{image.checksums.get('sha256', 'x' * 64)}",
                    local_path=image.path,
                )
                image.location = loc
    im.output_version = VERSION_2_0
    return im


# ---------------------------------------------------------------------------
# Tests: iter_all_locations
# ---------------------------------------------------------------------------


class TestIterAllLocations:
    """Tests for iter_all_locations generator."""

    def test_images_yields_entries(self):
        """Test that images produce LocationEntry tuples."""
        im = _create_images()
        entries = list(iter_all_locations(images=im))

        assert len(entries) == 2
        for e in entries:
            assert isinstance(e, LocationEntry)
            assert e.module_type == "image"
            assert e.variant == "Server"
            assert e.arch == "x86_64"
            assert e.path.startswith("Server/x86_64/iso/")

    def test_rpms_yields_entries(self):
        """Test that rpms produce LocationEntry tuples."""
        rpms = _create_rpms()
        entries = list(iter_all_locations(rpms=rpms))

        assert len(entries) == 1
        e = entries[0]
        assert e.module_type == "rpm"
        assert e.variant == "Server"
        assert e.arch == "x86_64"
        assert "bash" in e.path

    def test_extra_files_yields_entries(self):
        """Test that extra_files produce LocationEntry tuples."""
        ef = _create_extra_files()
        entries = list(iter_all_locations(extra_files=ef))

        assert len(entries) == 1
        e = entries[0]
        assert e.module_type == "extra_file"
        assert e.path == "Server/x86_64/os/GPL"

    def test_modules_yields_entries(self):
        """Test that modules produce LocationEntry tuples."""
        modules = _create_modules()
        entries = list(iter_all_locations(modules=modules))

        assert len(entries) == 1
        e = entries[0]
        assert e.module_type == "module"
        assert "modules.yaml.gz" in e.path

    def test_composeinfo_yields_variant_paths(self):
        """Test that composeinfo produces LocationEntry for each variant path."""
        ci = _create_composeinfo()
        entries = list(iter_all_locations(composeinfo=ci))

        # Server variant has os_tree and packages for x86_64 = 2 entries
        assert len(entries) == 2
        types = {e.module_type for e in entries}
        assert types == {"variant_path"}
        paths = {e.path for e in entries}
        assert "Server/x86_64/os" in paths
        assert "Server/x86_64/os/Packages" in paths

    def test_skips_none_modules(self):
        """Test that None modules are skipped."""
        im = _create_images()
        entries = list(iter_all_locations(images=im))

        # Only image entries, no rpm/module/etc
        module_types = {e.module_type for e in entries}
        assert module_types == {"image"}

    def test_all_modules_combined(self):
        """Test iteration across all module types."""
        im = _create_images()
        rpms = _create_rpms()
        ef = _create_extra_files()
        modules = _create_modules()
        ci = _create_composeinfo()

        entries = list(
            iter_all_locations(
                images=im,
                rpms=rpms,
                extra_files=ef,
                modules=modules,
                composeinfo=ci,
            )
        )

        module_types = {e.module_type for e in entries}
        assert module_types == {"image", "rpm", "extra_file", "module", "variant_path"}
        # 2 images + 1 rpm + 1 extra_file + 1 module + 2 variant_paths = 7
        assert len(entries) == 7

    def test_v1_data_has_none_locations(self):
        """Test that v1.x data yields location=None."""
        im = _create_images()
        entries = list(iter_all_locations(images=im))

        for e in entries:
            assert e.location is None

    def test_v2_data_has_location_objects(self):
        """Test that v2.0 data yields Location objects."""
        im = _create_images_v2()
        entries = list(iter_all_locations(images=im))

        for e in entries:
            assert e.location is not None
            assert isinstance(e.location, Location)

    def test_set_location_callback_images(self):
        """Test set_location callback sets image._location."""
        im = _create_images()
        entries = list(iter_all_locations(images=im))

        loc = Location(
            url="https://cdn.example.com/test.iso",
            size=512000000,
            checksum="sha256:" + "a" * 64,
            local_path="test.iso",
        )
        entries[0].set_location(loc)

        # Verify the location was set on the actual image object
        images_list = list(im.images["Server"]["x86_64"])
        found = any(img._location is not None and img._location.url == "https://cdn.example.com/test.iso" for img in images_list)
        assert found, "set_location should set _location on the Image object"

    def test_set_location_callback_rpms(self):
        """Test set_location callback sets rpm_data['_location']."""
        rpms = _create_rpms()
        entries = list(iter_all_locations(rpms=rpms))

        loc = Location(url="https://cdn.example.com/test.rpm", local_path="test.rpm")
        entries[0].set_location(loc)

        # Verify the location was set on the rpm data dict
        for srpm in rpms.rpms["Server"]["x86_64"].values():
            for rpm_data in srpm.values():
                if "_location" in rpm_data:
                    assert rpm_data["_location"] is loc
                    return
        pytest.fail("set_location should set _location on the RPM data dict")

    def test_set_location_callback_composeinfo(self):
        """Test set_location callback sets _locations on VariantPaths."""
        ci = _create_composeinfo()
        entries = list(iter_all_locations(composeinfo=ci))

        loc = Location(url="https://cdn.example.com/os/", local_path="Server/x86_64/os")
        # Find the os_tree entry and set its location
        for e in entries:
            if e.path == "Server/x86_64/os":
                e.set_location(loc)
                break

        server = ci.variants["Server"]
        assert server.paths._locations["os_tree"]["x86_64"] is loc


# ---------------------------------------------------------------------------
# Tests: upgrade_to_v2
# ---------------------------------------------------------------------------


class TestUpgradeToV2:
    """Tests for upgrade_to_v2 function."""

    def test_basic_upgrade_with_base_url(self):
        """Test upgrade produces v2.0 output with correct URLs."""
        im = _create_images()
        result = upgrade_to_v2(images=im, base_url="https://cdn.example.com/")

        assert "images" in result
        new_images = result["images"]
        assert new_images.output_version == VERSION_2_0

        # Check that locations were attached
        entries = list(iter_all_locations(images=new_images))
        for e in entries:
            assert e.location is not None
            assert e.location.url == f"https://cdn.example.com/{e.path}"
            assert e.location.local_path == e.path

    def test_url_mapper_overrides_base_url(self):
        """Test that url_mapper is used instead of base_url when provided."""
        im = _create_images()

        def mapper(local_path, variant, arch, module_type):
            return f"oci://registry.example.com/{variant}/{arch}/{os.path.basename(local_path)}"

        result = upgrade_to_v2(
            images=im,
            base_url="https://should-not-be-used.com/",
            url_mapper=mapper,
        )

        entries = list(iter_all_locations(images=result["images"]))
        for e in entries:
            assert e.location.url.startswith("oci://registry.example.com/Server/x86_64/")
            assert "should-not-be-used" not in e.location.url

    def test_url_mapper_receives_correct_args(self):
        """Test that url_mapper receives the correct arguments."""
        rpms = _create_rpms()
        calls = []

        def spy_mapper(local_path, variant, arch, module_type):
            calls.append((local_path, variant, arch, module_type))
            return f"https://mapped/{local_path}"

        upgrade_to_v2(rpms=rpms, url_mapper=spy_mapper)

        assert len(calls) == 1
        local_path, variant, arch, module_type = calls[0]
        assert "bash" in local_path
        assert variant == "Server"
        assert arch == "x86_64"
        assert module_type == "rpm"

    def test_compute_checksums(self, tmp_path):
        """Test compute_checksums populates checksum and size from local files."""
        # Create a fake file
        compose_dir = tmp_path / "compose"
        rpm_dir = compose_dir / "Server" / "x86_64" / "os" / "Packages" / "b"
        rpm_dir.mkdir(parents=True)
        rpm_file = rpm_dir / "bash-5.2.26-3.fc41.x86_64.rpm"
        rpm_file.write_text("fake rpm content")

        rpms = _create_rpms()
        result = upgrade_to_v2(
            rpms=rpms,
            base_url="https://cdn.example.com/",
            compute_checksums=True,
            compose_path=str(compose_dir),
        )

        entries = list(iter_all_locations(rpms=result["rpms"]))
        e = entries[0]
        assert e.location.checksum is not None
        assert e.location.checksum.startswith("sha256:")
        assert e.location.size == len("fake rpm content")

    def test_compute_checksums_requires_compose_path(self):
        """Test that compute_checksums=True without compose_path raises ValueError."""
        im = _create_images()
        with pytest.raises(ValueError, match="compose_path is required"):
            upgrade_to_v2(images=im, compute_checksums=True)

    def test_output_files_written(self, tmp_path):
        """Test that metadata files are written to output_dir."""
        im = _create_images()
        rpms = _create_rpms()
        output_dir = str(tmp_path / "v2-output")

        upgrade_to_v2(
            output_dir=output_dir,
            images=im,
            rpms=rpms,
            base_url="https://cdn.example.com/",
        )

        assert os.path.isfile(os.path.join(output_dir, "images.json"))
        assert os.path.isfile(os.path.join(output_dir, "rpms.json"))
        assert not os.path.exists(os.path.join(output_dir, "modules.json"))

    def test_originals_not_modified(self):
        """Test that original metadata objects are not modified."""
        im = _create_images()

        # Capture original state
        original_entries = list(iter_all_locations(images=im))
        assert all(e.location is None for e in original_entries)

        # Upgrade
        upgrade_to_v2(images=im, base_url="https://cdn.example.com/")

        # Originals should be unchanged
        original_entries = list(iter_all_locations(images=im))
        assert all(e.location is None for e in original_entries)

    def test_returns_upgraded_objects(self):
        """Test return dict has correct keys and v2.0 output_version."""
        im = _create_images()
        rpms = _create_rpms()

        result = upgrade_to_v2(images=im, rpms=rpms, base_url="https://cdn.example.com/")

        assert set(result.keys()) == {"images", "rpms"}
        assert result["images"].output_version == VERSION_2_0
        assert result["rpms"].output_version == VERSION_2_0

    def test_only_provided_modules_upgraded(self):
        """Test that only provided modules appear in the result."""
        im = _create_images()
        result = upgrade_to_v2(images=im, base_url="https://cdn.example.com/")

        assert "images" in result
        assert "rpms" not in result
        assert "modules" not in result

    def test_upgrade_all_modules(self):
        """Test upgrading all module types simultaneously."""
        im = _create_images()
        rpms = _create_rpms()
        ef = _create_extra_files()
        modules = _create_modules()
        ci = _create_composeinfo()

        result = upgrade_to_v2(
            images=im,
            rpms=rpms,
            extra_files=ef,
            modules=modules,
            composeinfo=ci,
            base_url="https://cdn.example.com/",
        )

        assert set(result.keys()) == {"images", "rpms", "extra_files", "modules", "composeinfo"}
        for obj in result.values():
            assert obj.output_version == VERSION_2_0


# ---------------------------------------------------------------------------
# Tests: downgrade_to_v1
# ---------------------------------------------------------------------------


class TestDowngradeToV1:
    """Tests for downgrade_to_v1 function."""

    def test_basic_downgrade(self):
        """Test downgrade produces v1.2 output."""
        im = _create_images_v2()
        result = downgrade_to_v1(images=im)

        assert "images" in result
        assert result["images"].output_version == VERSION_1_2

    def test_paths_from_local_path(self):
        """Test that v1.2 paths come from Location.local_path."""
        im = _create_images_v2()
        result = downgrade_to_v1(images=im)

        # Serialize as v1.2 and check paths
        data = {}
        result["images"].serialize(data)

        images_data = data["payload"]["images"]["Server"]["x86_64"]
        for img in images_data:
            assert "path" in img
            assert "location" not in img
            assert img["path"].startswith("Server/x86_64/iso/")

    def test_output_files_written(self, tmp_path):
        """Test that metadata files are written to output_dir."""
        im = _create_images_v2()
        output_dir = str(tmp_path / "v1-output")

        downgrade_to_v1(output_dir=output_dir, images=im)

        assert os.path.isfile(os.path.join(output_dir, "images.json"))

    def test_originals_not_modified(self):
        """Test that original metadata objects are not modified."""
        im = _create_images_v2()
        original_version = im.output_version

        downgrade_to_v1(images=im)

        assert im.output_version == original_version

    def test_returns_downgraded_objects(self):
        """Test return dict has correct keys and v1.2 output_version."""
        im = _create_images_v2()
        rpms = _create_rpms()

        result = downgrade_to_v1(images=im, rpms=rpms)

        assert set(result.keys()) == {"images", "rpms"}
        assert result["images"].output_version == VERSION_1_2
        assert result["rpms"].output_version == VERSION_1_2


# ---------------------------------------------------------------------------
# Tests: Round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Tests for round-trip conversion."""

    def test_upgrade_then_downgrade_preserves_paths(self):
        """Test v1.2 -> upgrade -> downgrade preserves paths."""
        im = _create_images()

        # Collect original paths
        original_paths = {e.path for e in iter_all_locations(images=im)}

        # Upgrade to v2.0
        upgraded = upgrade_to_v2(images=im, base_url="https://cdn.example.com/")

        # Downgrade back to v1.2
        downgraded = downgrade_to_v1(images=upgraded["images"])

        # Paths should be preserved
        final_paths = {e.path for e in iter_all_locations(images=downgraded["images"])}
        assert original_paths == final_paths

    def test_downgrade_then_upgrade(self):
        """Test v2.0 -> downgrade -> upgrade produces valid v2.0 output."""
        im = _create_images_v2()

        # Downgrade to v1.2
        downgraded = downgrade_to_v1(images=im)

        # Upgrade back to v2.0 (URLs are regenerated, not preserved from original)
        upgraded = upgrade_to_v2(
            images=downgraded["images"],
            base_url="https://new-cdn.example.com/",
        )

        # Verify v2.0 structure
        entries = list(iter_all_locations(images=upgraded["images"]))
        for e in entries:
            assert e.location is not None
            assert e.location.url.startswith("https://new-cdn.example.com/")
            assert e.location.local_path == e.path
