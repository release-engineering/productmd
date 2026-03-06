"""Tests for loading and validating v2.0 compose metadata test files."""

import json
import os

import pytest

# Path to v2.0 test files
V2_TEST_DIR = os.path.join(os.path.dirname(__file__), "compose-v2", "metadata")


def _find_all_urls(obj):
    """Recursively find all 'url' values in a nested structure."""
    urls = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "url" and isinstance(value, str):
                urls.append(value)
            else:
                urls.extend(_find_all_urls(value))
    elif isinstance(obj, list):
        for item in obj:
            urls.extend(_find_all_urls(item))
    return urls


def _find_all_checksums(obj):
    """Recursively find all 'checksum' values in a nested structure."""
    checksums = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "checksum" and isinstance(value, str):
                checksums.append(value)
            else:
                checksums.extend(_find_all_checksums(value))
    elif isinstance(obj, list):
        for item in obj:
            checksums.extend(_find_all_checksums(item))
    return checksums


def _load_v2_json(filename):
    """Load a JSON file from the v2 test directory."""
    path = os.path.join(V2_TEST_DIR, filename)
    with open(path, "r") as f:
        return json.load(f)


def _list_v2_json_files():
    """List all JSON files in the v2 test directory."""
    return [f for f in os.listdir(V2_TEST_DIR) if f.endswith(".json")]


class TestV2ComposeFiles:
    """Test that v2.0 compose test files are valid JSON and have correct structure."""

    def test_composeinfo_v2_structure(self):
        """Test composeinfo.json v2.0 structure."""
        data = _load_v2_json("composeinfo.json")

        # Check header
        assert data["header"]["version"] == "2.0"
        assert data["header"]["type"] == "productmd.composeinfo"

        # Check payload structure
        payload = data["payload"]
        assert "compose" in payload
        assert "release" in payload
        assert "variants" in payload

        # Check variant paths have Location structure
        server = payload["variants"]["Server"]
        assert server["id"] == "Server"
        assert "paths" in server

        # Check os_tree path is a Location object (not a plain string)
        os_tree_x86 = server["paths"]["os_tree"]["x86_64"]
        assert isinstance(os_tree_x86, dict), "v2.0 paths should be Location objects, not strings"
        assert "url" in os_tree_x86
        assert "size" in os_tree_x86
        assert "checksum" in os_tree_x86
        assert "local_path" in os_tree_x86
        assert os_tree_x86["checksum"].startswith("sha256:")

    def test_composeinfo_v2_path_categories(self):
        """Test composeinfo.json v2.0 has repository, source, and debug path categories."""
        data = _load_v2_json("composeinfo.json")
        server_paths = data["payload"]["variants"]["Server"]["paths"]

        # repository path (YUM repo, checksum is of repomd.xml per plan Section 6)
        assert "repository" in server_paths
        repo = server_paths["repository"]["x86_64"]
        assert "url" in repo
        assert "checksum" in repo

        # source paths
        assert "source_tree" in server_paths
        assert "source_packages" in server_paths
        src_tree = server_paths["source_tree"]["x86_64"]
        assert src_tree["checksum"].startswith("sha256:")

        # debug paths
        assert "debug_tree" in server_paths
        assert "debug_packages" in server_paths
        dbg_tree = server_paths["debug_tree"]["x86_64"]
        assert dbg_tree["checksum"].startswith("sha256:")

    def test_composeinfo_v2_addon_variant(self):
        """Test composeinfo.json v2.0 has an addon variant type."""
        data = _load_v2_json("composeinfo.json")
        variants = data["payload"]["variants"]

        # Check Server-HA addon variant exists
        assert "Server-HA" in variants
        ha = variants["Server-HA"]
        assert ha["type"] == "addon"
        assert ha["id"] == "HA"
        assert ha["uid"] == "Server-HA"
        assert "paths" in ha
        assert "repository" in ha["paths"]

    def test_images_v2_structure(self):
        """Test images.json v2.0 structure."""
        data = _load_v2_json("images.json")

        # Check header
        assert data["header"]["version"] == "2.0"
        assert data["header"]["type"] == "productmd.images"

        # Check images have location instead of path
        images = data["payload"]["images"]
        server_x86 = images["Server"]["x86_64"]
        assert len(server_x86) > 0

        # Check first image has Location structure
        img = server_x86[0]
        assert "location" in img
        assert "path" not in img  # v2.0 uses location, not path
        assert "checksums" not in img  # v2.0 uses location.checksum

        loc = img["location"]
        assert "url" in loc
        assert "size" in loc
        assert "checksum" in loc
        assert "local_path" in loc

    def test_images_oci_contents_structure(self):
        """Test images-oci-contents.json with OCI contents structure."""
        data = _load_v2_json("images-oci-contents.json")

        # Check header
        assert data["header"]["version"] == "2.0"

        # Find boot image with contents
        images = data["payload"]["images"]["Server"]["x86_64"]
        boot_images = [i for i in images if i.get("type") == "boot"]
        assert len(boot_images) > 0

        boot_img = boot_images[0]
        loc = boot_img["location"]

        # Check it's an OCI reference
        assert loc["url"].startswith("oci://")

        # Check contents array
        assert "contents" in loc
        contents = loc["contents"]
        assert len(contents) > 0

        # Check FileEntry structure
        file_entry = contents[0]
        assert "file" in file_entry
        assert "size" in file_entry
        assert "checksum" in file_entry
        assert "layer_digest" in file_entry
        assert file_entry["checksum"].startswith("sha256:")
        assert file_entry["layer_digest"].startswith("sha256:")

    def test_rpms_v2_structure(self):
        """Test rpms.json v2.0 structure."""
        data = _load_v2_json("rpms.json")

        # Check header
        assert data["header"]["version"] == "2.0"
        assert data["header"]["type"] == "productmd.rpms"

        # Check RPMs have location
        rpms = data["payload"]["rpms"]
        server_x86 = rpms["Server"]["x86_64"]
        assert len(server_x86) > 0

        # Get first SRPM and its binary RPMs
        srpm_key = list(server_x86.keys())[0]
        srpm_rpms = server_x86[srpm_key]
        rpm_key = list(srpm_rpms.keys())[0]
        rpm = srpm_rpms[rpm_key]

        # Check RPM has location and v2.0 fields
        assert "location" in rpm
        assert "sigkey" in rpm
        assert "category" in rpm
        assert "path" not in rpm  # v2.0 uses location, not path

        loc = rpm["location"]
        assert "url" in loc
        assert "size" in loc
        assert "checksum" in loc
        assert "local_path" in loc

    def test_rpms_v2_categories(self):
        """Test rpms.json v2.0 has binary, source, and debug RPM categories."""
        data = _load_v2_json("rpms.json")
        server_x86 = data["payload"]["rpms"]["Server"]["x86_64"]

        # Collect all categories across all RPM entries
        categories = set()
        for srpm_rpms in server_x86.values():
            for rpm in srpm_rpms.values():
                categories.add(rpm["category"])

        assert "binary" in categories, "fixture should have binary RPMs"
        assert "source" in categories, "fixture should have source RPMs"
        assert "debug" in categories, "fixture should have debug RPMs"

    def test_rpms_v2_unsigned_rpm(self):
        """Test rpms.json v2.0 has at least one unsigned RPM (sigkey: null)."""
        data = _load_v2_json("rpms.json")
        server_x86 = data["payload"]["rpms"]["Server"]["x86_64"]

        has_null_sigkey = False
        for srpm_rpms in server_x86.values():
            for rpm in srpm_rpms.values():
                if rpm["sigkey"] is None:
                    has_null_sigkey = True
                    break

        assert has_null_sigkey, "fixture should have at least one unsigned RPM (sigkey: null)"

    def test_extra_files_v2_structure(self):
        """Test extra_files.json v2.0 structure."""
        data = _load_v2_json("extra_files.json")

        # Check header
        assert data["header"]["version"] == "2.0"
        assert data["header"]["type"] == "productmd.extra_files"

        # Check extra files have location
        extra_files = data["payload"]["extra_files"]
        server_x86 = extra_files["Server"]["x86_64"]
        assert len(server_x86) > 0

        # Check first file has Location structure (v2.0 format)
        file_entry = server_x86[0]
        assert "file" in file_entry
        assert "location" in file_entry
        assert "size" not in file_entry  # v2.0 moves size into location
        assert "checksums" not in file_entry  # v2.0 uses location.checksum

        loc = file_entry["location"]
        assert "url" in loc
        assert "size" in loc
        assert "checksum" in loc
        assert "local_path" in loc

    def test_modules_v2_structure(self):
        """Test modules.json v2.0 structure."""
        data = _load_v2_json("modules.json")

        # Check header
        assert data["header"]["version"] == "2.0"
        assert data["header"]["type"] == "productmd.modules"

        # Check modules have location
        modules = data["payload"]["modules"]
        server_x86 = modules["Server"]["x86_64"]
        assert len(server_x86) > 0

        # Get first module
        mod_key = list(server_x86.keys())[0]
        module = server_x86[mod_key]

        # Check module structure
        assert "name" in module
        assert "stream" in module
        assert "version" in module
        assert "context" in module
        assert "arch" in module
        assert "rpms" in module
        assert "location" in module

        # Check location
        loc = module["location"]
        assert "url" in loc
        assert "checksum" in loc

    def test_modules_v2_local_path_is_file(self):
        """Test that HTTPS module local_path points to a file, not a directory."""
        data = _load_v2_json("modules.json")
        pg = data["payload"]["modules"]["Server"]["x86_64"]["postgresql:16:4120250101223344:f41:x86_64"]

        # HTTPS module should have a file-level local_path
        loc = pg["location"]
        assert loc["url"].startswith("https://")
        assert loc["local_path"].endswith(".yaml.gz"), f"HTTPS module local_path should point to a modulemd file, got: {loc['local_path']}"

    @pytest.mark.parametrize("filename", _list_v2_json_files())
    def test_all_urls_are_valid_format(self, filename):
        """Test that all URLs in a v2.0 file are valid format."""
        valid_prefixes = ("https://", "http://", "oci://")
        data = _load_v2_json(filename)

        urls = _find_all_urls(data)
        for url in urls:
            assert url.startswith(valid_prefixes), f"Invalid URL format in {filename}: {url}"

    @pytest.mark.parametrize("filename", _list_v2_json_files())
    def test_all_checksums_are_sha256(self, filename):
        """Test that all checksums in a v2.0 file use sha256: prefix."""
        data = _load_v2_json(filename)

        checksums = _find_all_checksums(data)
        for checksum in checksums:
            assert checksum.startswith("sha256:"), f"Invalid checksum format in {filename}: {checksum}"
