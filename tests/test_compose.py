#!/usr/bin/env python3

# Copyright (C) 2015  Red Hat, Inc.
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


import unittest

import json
import os
import shutil
import sys
import tempfile
import urllib.request

DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(DIR, ".."))

from productmd.compose import Compose  # noqa

from io import StringIO  # noqa
from urllib.error import HTTPError  # noqa


class TestCompose(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compose_path = os.path.join(DIR, "compose")

    def test_read_composeinfo(self):
        compose = Compose(self.compose_path)
        compose.info

        # try to access a variant and addon
        variant = compose.info["Foo"]  # noqa: F841
        variant = compose.info["Foo-Bar"]  # noqa: F841

    def test_opening_wrong_dir_gives_descriptive_error(self):
        compose = Compose('/a/b/c')
        try:
            compose.rpms
            self.fail('Accessing the attribute must raise exception')
        except RuntimeError as e:
            self.assertEqual(str(e), r"Failed to load metadata from /a/b/c")
        except:  # noqa: E722
            self.fail('Expected to get RuntimeError')

    def test_opening_http_succeeds(self):
        def mock_urlopen(url, context=None):
            """Return an on-disk JSON file's contents for a given url."""
            # Handle both string URLs and Request objects
            if isinstance(url, urllib.request.Request):
                url = url.full_url
            filename = os.path.basename(url)
            if not filename.endswith('.json'):
                # This is not parsed; it just needs to be any 200 OK response.
                return StringIO()
            try:
                f = open(os.path.join(self.compose_path, "compose", "metadata", filename), 'r')
            except IOError as e:
                raise HTTPError(404, e)
            return f

        orig_urlopen = urllib.request.urlopen
        try:
            urllib.request.urlopen = mock_urlopen
            compose = Compose('http://example.noexist/path/to/mycompose')
            self.assertEqual('MYPRODUCT', compose.info.release.short)
        finally:
            urllib.request.urlopen = orig_urlopen


class TestLegacyCompose(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compose_path = os.path.join(DIR, "compose-legacy")

    def test_read_composeinfo(self):
        compose = Compose(self.compose_path)
        compose.info

        # try to access a variant and addon
        variant = compose.info["Foo"]  # noqa: F841
        variant = compose.info["Foo-Bar"]  # noqa: F841


class TestComposeErrorHandling(unittest.TestCase):
    """Test Compose._load_metadata error handling with v1.x format data.

    Addresses https://github.com/release-engineering/productmd/issues/110:
    error messages should distinguish invalid JSON from unsupported field values.
    """

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        # Build a minimal compose directory: <tmp>/compose/metadata/
        self.metadata_dir = os.path.join(self.tmp_dir, "compose", "metadata")
        os.makedirs(self.metadata_dir)
        # Write a valid v1.2 composeinfo.json so Compose.__init__ finds it
        composeinfo = {
            "header": {"type": "productmd.composeinfo", "version": "1.2"},
            "payload": {
                "compose": {
                    "date": "20180101",
                    "id": "Test-1.0-20180101.0",
                    "respin": 0,
                    "type": "production",
                },
                "release": {
                    "name": "Test",
                    "short": "Test",
                    "version": "1.0",
                    "type": "ga",
                },
                "variants": {},
            },
        }
        with open(os.path.join(self.metadata_dir, "composeinfo.json"), "w") as f:
            json.dump(composeinfo, f)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def _build_v1_images_data(self, image_type="dvd"):
        return {
            "header": {"type": "productmd.images", "version": "1.1"},
            "payload": {
                "compose": {
                    "date": "20180101",
                    "id": "Test-1.0-20180101.0",
                    "respin": 0,
                    "type": "production",
                },
                "images": {
                    "Server": {
                        "x86_64": [
                            {
                                "arch": "x86_64",
                                "bootable": True,
                                "checksums": {"sha256": "a" * 64},
                                "disc_count": 1,
                                "disc_number": 1,
                                "format": "iso",
                                "implant_md5": "b" * 32,
                                "mtime": 1514764800,
                                "path": "Server/x86_64/iso/test.iso",
                                "size": 2147483648,
                                "subvariant": "Server",
                                "type": image_type,
                                "volume_id": "Test-1.0",
                            }
                        ]
                    }
                },
            },
        }

    def _write_images(self, content):
        path = os.path.join(self.metadata_dir, "images.json")
        with open(path, "w") as f:
            if isinstance(content, str):
                f.write(content)
            else:
                json.dump(content, f)

    def test_invalid_json_mentions_not_valid_json(self):
        self._write_images("{not valid json")
        compose = Compose(self.tmp_dir)
        with self.assertRaises(RuntimeError) as ctx:
            compose.images
        self.assertIn("not valid JSON", str(ctx.exception))

    def test_unknown_image_type_error_message(self):
        """Unknown type should say 'not supported' with the bad value, not 'not valid JSON'."""
        self._write_images(self._build_v1_images_data(image_type="future-hologram"))
        compose = Compose(self.tmp_dir)
        with self.assertRaises(RuntimeError) as ctx:
            compose.images
        msg = str(ctx.exception)
        self.assertIn("not supported", msg)
        self.assertIn("future-hologram", msg)
        self.assertNotIn("not valid JSON", msg)


if __name__ == "__main__":
    unittest.main()
