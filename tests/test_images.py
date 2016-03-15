#!/usr/bin/python
# -*- coding: utf-8 -*-


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

import os
import sys
import tempfile
import shutil

DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(DIR, ".."))

from productmd.images import Images, Image


class TestImages(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def assertSameFiles(self, path1, path2):
        self.assertEqual(os.path.getsize(path1), os.path.getsize(path2))
        file1 = open(path1, "r")
        file2 = open(path2, "r")
        self.assertEqual(file1.read(), file2.read())
        file1.close()
        file2.close()

    def _test_identity(self, im):
        first = os.path.join(self.tmp_dir, "first")
        second = os.path.join(self.tmp_dir, "second")

        # write original file
        im.dump(first)

        # read file and write it back
        im = Images()
        im.load(first)
        im.dump(second)

        # check if first and second files are identical
        self.assertSameFiles(first, second)

    def test_fedora_20(self):
        im = Images()
        im.header.version = "1.0"
        im.compose.id = "Fedora-20-20131212.0"
        im.compose.type = "production"
        im.compose.date = "20131212"
        im.compose.respin = 0

        i = Image(im)
        i.path = "Fedora/x86_64/iso/Fedora-20-x86_64-DVD.iso"
        i.mtime = 1410855216
        i.size = 4603248640
        i.arch = "x86_64"
        i.type = "dvd"
        i.format = "iso"
        i.disc_number = 1
        i.disc_count = 1
        i.volume_id = "Fedora 20 x86_64"

        # checksums
        i.add_checksum(root=None, checksum_type="sha256", checksum_value="f2eeed5102b8890e9e6f4b9053717fe73031e699c4b76dc7028749ab66e7f917")
        i.add_checksum(root=None, checksum_type="sha1", checksum_value="36dd25d7a6df45cdf19b85ad1bf2a2ccbf34f991")
        i.add_checksum(root=None, checksum_type="md5", checksum_value="9a190c8b2bd382c2d046dbc855cd2f2b")
        self.assertEqual(i.checksums, {
            "sha256": "f2eeed5102b8890e9e6f4b9053717fe73031e699c4b76dc7028749ab66e7f917",
            "sha1": "36dd25d7a6df45cdf19b85ad1bf2a2ccbf34f991",
            "md5": "9a190c8b2bd382c2d046dbc855cd2f2b",
        })
        self.assertRaises(ValueError, i.add_checksum, root=None, checksum_type="sha256", checksum_value="foo")

        i.implant_md5 = "b39b2f6770ca015f300af01cb54db75c"
        i.bootable = True
        im.add("Fedora", "x86_64", i)

        i = Image(im)
        i.path = "Fedora/x86_64/iso/Fedora-20-x86_64-netinst.iso"
        i.mtime = 1410855243
        i.size = 336592896
        i.arch = "x86_64"
        i.type = "netinst"
        i.format = "iso"
        i.disc_number = 1
        i.disc_count = 1
        i.volume_id = "Fedora 20 x86_64"

        # checksums
        i.add_checksum(root=None, checksum_type="sha256", checksum_value="376be7d4855ad6281cb139430606a782fd6189dcb01d7b61448e915802cc350f")
        i.add_checksum(root=None, checksum_type="sha1", checksum_value="cb8b3e285fc1336cbbd7ba4b0381095dd0e159b0")
        i.add_checksum(root=None, checksum_type="md5", checksum_value="82716caf39ce9fd88e7cfc66ca219db8")
        self.assertEqual(i.checksums, {
            "sha256": "376be7d4855ad6281cb139430606a782fd6189dcb01d7b61448e915802cc350f",
            "sha1": "cb8b3e285fc1336cbbd7ba4b0381095dd0e159b0",
            "md5": "82716caf39ce9fd88e7cfc66ca219db8",
        })
        self.assertRaises(ValueError, i.add_checksum, root=None, checksum_type="sha256", checksum_value="foo")

        i.implant_md5 = "62cc05b03d28881c88ff1e949d6fc0b7"
        i.bootable = True
        im.add("Fedora", "x86_64", i)

        # im.dump("image_manifest.json")

        self._test_identity(im)

        # 1 arch
        self.assertEqual(len(im["Fedora"]), 1)

        # 2 images
        self.assertEqual(len(im["Fedora"]["x86_64"]), 2)

    def test_image_repr(self):
        i = Image(None)
        i.path = "Fedora/x86_64/iso/Fedora-20-x86_64-DVD.iso"
        i.mtime = 1410855216
        i.size = 4603248640
        i.arch = "x86_64"
        i.type = "dvd"
        i.format = "iso"
        i.disc_number = 1
        i.disc_count = 1
        i.volume_id = "Fedora 20 x86_64"

        self.assertEqual(
            repr(i),
            '<Image:Fedora/x86_64/iso/Fedora-20-x86_64-DVD.iso:iso:x86_64>')

    def test_image_repr_incomplete(self):
        i = Image(None)

        self.assertEqual(repr(i), '<Image:None:None:None>')


if __name__ == "__main__":
    unittest.main()
