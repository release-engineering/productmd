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

from productmd.images import Images, Image, identify_image  # noqa


class TestImages(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def assertSameFiles(self, path1, path2):
        self.assertEqual(os.path.getsize(path1), os.path.getsize(path2))
        with open(path1, "r") as file1:
            with open(path2, "r") as file2:
                self.assertEqual(file1.read(), file2.read())

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
        i.subvariant = ""

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
        i.subvariant = ""

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

        # im.dump("f20.json")

        self._test_identity(im)

        # Server: 1 arch, 2 images
        self.assertEqual(len(im["Fedora"]), 1)
        self.assertEqual(len(im["Fedora"]["x86_64"]), 2)

    def test_fedora_23(self):
        im = Images()
        im.header.version = "1.0"
        im.compose.id = "Fedora-23-20151030.0"
        im.compose.type = "production"
        im.compose.date = "20151030"
        im.compose.respin = 0

        i = Image(im)
        i.path = "Server/x86_64/iso/Fedora-Server-DVD-x86_64-23.iso"
        i.mtime = 1446169817
        i.size = 2149580800
        i.arch = "x86_64"
        i.type = "dvd"
        i.format = "iso"
        i.disc_number = 1
        i.disc_count = 1
        i.volume_id = "Fedora-S-23-x86_64"
        i.subvariant = ""

        # checksums
        i.add_checksum(root=None, checksum_type="sha256", checksum_value="30758dc821d1530de427c9e35212bd79b058bd4282e64b7b34ae1a40c87c05ae")
        self.assertEqual(i.checksums, {
            "sha256": "30758dc821d1530de427c9e35212bd79b058bd4282e64b7b34ae1a40c87c05ae",
        })
        self.assertRaises(ValueError, i.add_checksum, root=None, checksum_type="sha256", checksum_value="foo")

        i.implant_md5 = "1cd120922a791d03e829392a2b6b2107"
        i.bootable = True
        im.add("Server", "x86_64", i)

        i = Image(im)
        i.path = "Server/x86_64/iso/Fedora-Server-netinst-x86_64-23.iso"
        i.mtime = 1458057407
        i.size = 8011776
        i.arch = "x86_64"
        i.type = "netinst"
        i.format = "iso"
        i.disc_number = 1
        i.disc_count = 1
        i.volume_id = "Fedora-S-23-x86_64"
        i.subvariant = ""

        # checksums
        i.add_checksum(root=None, checksum_type="sha256", checksum_value="32e0a15a1c71d0e2fd36a0af5b67a3b3af82976d2dfca0aefcb90d42f2ae6844")
        self.assertEqual(i.checksums, {
            "sha256": "32e0a15a1c71d0e2fd36a0af5b67a3b3af82976d2dfca0aefcb90d42f2ae6844",
        })
        self.assertRaises(ValueError, i.add_checksum, root=None, checksum_type="sha256", checksum_value="foo")

        i.implant_md5 = "6ccc75afc55855ece24ee84e62e6dcc0"
        i.bootable = True
        im.add("Server", "x86_64", i)

        i = Image(im)
        i.path = "Live/x86_64/iso/Fedora-Live-KDE-x86_64-23-10.iso"
        i.mtime = 1446154932
        i.size = 1291845632
        i.arch = "x86_64"
        i.type = "live"
        i.format = "iso"
        i.disc_number = 1
        i.disc_count = 1
        i.volume_id = "Fedora-Live-KDE-x86_64-23-10"
        i.subvariant = "KDE"

        # checksums
        i.add_checksum(root=None, checksum_type="sha256", checksum_value="ef7e5ed9eee6dbcde1e0a4d69c76ce6fb552f75ccad879fa0f93031ceb950f27")
        self.assertEqual(i.checksums, {
            "sha256": "ef7e5ed9eee6dbcde1e0a4d69c76ce6fb552f75ccad879fa0f93031ceb950f27",
        })
        self.assertRaises(ValueError, i.add_checksum, root=None, checksum_type="sha256", checksum_value="foo")
        # identifier (Image instance)
        self.assertEqual(identify_image(i), ("KDE", "live", "iso", "x86_64", 1, False, []))
        # identifier (dict)
        parser = []
        i.serialize(parser)
        imgdict = parser[0]
        self.assertEqual(identify_image(imgdict), ("KDE", "live", "iso", "x86_64", 1, False, []))

        i.implant_md5 = "8bc179ecdd48e0b019365104f081a83e"
        i.bootable = True
        im.add("Live", "x86_64", i)

        # im.dump("f23.json")

        self._test_identity(im)

        # Server: 1 arch, 2 images
        self.assertEqual(len(im["Server"]), 1)
        self.assertEqual(len(im["Server"]["x86_64"]), 2)

        # Live: 1 arch, 1 images
        self.assertEqual(len(im["Live"]), 1)
        self.assertEqual(len(im["Live"]["x86_64"]), 1)

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

    def test_f20_format_10(self):
        im = Images()
        im.load(os.path.join(DIR, "images/f20.json"))

    def test_f23_format_11(self):
        im = Images()
        im.load(os.path.join(DIR, "images/f23.json"))

    def test_forbidden_src_arch(self):
        """
        Test: ValueError("Source arch is not allowed. Map source files under binary arches.")
        """
        im = Images()
        i = Image(im)
        self.assertRaises(ValueError, im.add, "Server", "src", i)

    def test_move_src_images_under_binary_arches(self):
        """
        Test if src images were moved under binary arches correctly.
        """
        before = os.path.join(DIR, "images/src_move_before.json")
        after = os.path.join(DIR, "images/src_move_after.json")
        converted = os.path.join(self.tmp_dir, "converted")

        im = Images()
        im.load(before)

        self._test_identity(im)

        im.dump(converted)
        self.assertSameFiles(converted, after)

    def test_unified_iso_serialized_only_with_true(self):
        i = Image(None)
        i.arch = 'x86_64'
        i.disc_count = 1
        i.disc_number = 1
        i.format = 'iso'
        i.type = 'dvd'
        i.mtime = 1410855216
        i.path = "Fedora/x86_64/iso/Fedora-20-x86_64-DVD.iso"
        i.size = 4603248640
        i.subvariant = 'Workstation'
        i.checksums = {'sha256': 'XXXXXX'}

        data = []
        i.serialize(data)
        self.assertFalse('unified' in data[0])

        i.unified = True
        data = []
        i.serialize(data)
        self.assertTrue(data[0]['unified'])

    def test_unified_iso_deserialize(self):
        im = Images()
        i = Image(im)

        data = {
            'arch': 'x86_64',
            'disc_count': 1,
            'disc_number': 1,
            'format': 'iso',
            'type': 'dvd',
            'mtime': 1410855216,
            'path': "Fedora/x86_64/iso/Fedora-20-x86_64-DVD.iso",
            'size': 4603248640,
            'subvariant': 'Workstation',
            'volume_id': None,
            'implant_md5': None,
            'bootable': True,
            'checksums': {'sha256': 'XXXXXX'},
        }

        i.deserialize(data)
        self.assertFalse(i.unified)

        data['unified'] = True
        i.deserialize(data)
        self.assertTrue(i.unified)

    def test_unique_id_enforcement(self):
        """Test that adding two images with different checksums but
        matching UNIQUE_IMAGE_ATTRIBUTES is disallowed (on 1.1+).
        """
        im = Images()
        im.header.version = '1.1'

        i1 = Image(im)
        i2 = Image(im)
        data = {
            'arch': 'x86_64',
            'disc_count': 1,
            'disc_number': 1,
            'format': 'iso',
            'type': 'dvd',
            'mtime': 1410855216,
            'path': "Fedora/x86_64/iso/Fedora-20-x86_64-DVD.iso",
            'size': 4603248640,
            'subvariant': 'Workstation',
            'volume_id': None,
            'implant_md5': None,
            'bootable': True,
        }
        # NOTE: there's a rather subtle behaviour here where when you
        # deserialize, mutable things in the deserialized object are
        # not *copies* of the objects in the dict you deserialized
        # but *are* those objects. So if you modify them in the dict
        # after deserialization, *the deserialized object changes*.
        # I'm not sure whether this is intentional, but it means we
        # must be careful here, we cannot just deserialize i1, change
        # the checksums in data, then deserialize i2; if we do that,
        # i1's checksums are changed, the checksums for i1 and i2
        # match, and the expected error isn't triggered.
        data1 = dict(data)
        data1['checksums'] = {'sha256': 'XXXXXX'}
        i1.deserialize(data1)
        im.add("Workstation", "x86_64", i1)

        data2 = dict(data)
        data2['checksums'] = {'sha256': 'YYYYYY'}
        i2.deserialize(data2)
        self.assertRaises(ValueError, im.add, "Server", "x86_64", i2)

if __name__ == "__main__":
    unittest.main()
