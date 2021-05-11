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

from productmd.treeinfo import TreeInfo, Variant  # noqa


class TestTreeInfo(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestTreeInfo, self).__init__(*args, **kwargs)
        self.treeinfo_path = os.path.join(DIR, "treeinfo")

    def setUp(self):
        self.maxDiff = None
        self.tmp_dir = tempfile.mkdtemp()
        self.ini_path = os.path.join(self.tmp_dir, "treeinfo")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def assertSameFiles(self, path1, path2):
        self.assertEqual(os.path.getsize(path1), os.path.getsize(path2))
        with open(path1, "r") as file1:
            with open(path2, "r") as file2:
                self.assertEqual(file1.read(), file2.read())

    def _test_identity(self, ti):
        first = os.path.join(self.tmp_dir, "first")
        second = os.path.join(self.tmp_dir, "second")

        # write original file
        ti.dump(first)

        # read file and write it back
        ti = TreeInfo()
        ti.load(first)
        ti.dump(second)

        # check if first and second files are identical
        self.assertSameFiles(first, second)

    def test_create(self):
        ti = TreeInfo()
        ti.release.name = "Fedora"
        ti.release.short = "F"
        ti.release.version = "20"

        ti.tree.arch = "x86_64"
        ti.tree.build_timestamp = 123456

        variant = Variant(ti)
        variant.id = "Fedora"
        variant.uid = "Fedora"
        variant.name = "Fedora"
        variant.type = "variant"

        variant.paths.repository = "repo"
        variant.paths.packages = "pkgs"
        variant.paths.source_repository = "src repo"
        variant.paths.source_packages = "src pkgs"
        variant.paths.debug_repository = "debug repo"
        variant.paths.debug_packages = "debug pkgs"
        variant.paths.identity = "cert.pem"

        ti.variants.add(variant)

        ti.dump(self.ini_path)
        self._test_identity(ti)

    def test_create_with_two_variants(self):
        ti = TreeInfo()
        ti.release.name = "Fedora"
        ti.release.short = "F"
        ti.release.version = "20"

        ti.tree.arch = "x86_64"
        ti.tree.build_timestamp = 123456

        variant_1 = Variant(ti)
        variant_1.id = "AppStream"
        variant_1.uid = "AppStream"
        variant_1.name = "AppStream"
        variant_1.type = "variant"

        variant_1.paths.repository = "repo"
        variant_1.paths.packages = "pkgs"
        variant_1.paths.source_repository = "src repo"
        variant_1.paths.source_packages = "src pkgs"
        variant_1.paths.debug_repository = "debug repo"
        variant_1.paths.debug_packages = "debug pkgs"
        variant_1.paths.identity = "cert.pem"

        ti.variants.add(variant_1)

        variant_2 = Variant(ti)
        variant_2.id = "BaseOS"
        variant_2.uid = "BaseOS"
        variant_2.name = "BaseOS"
        variant_2.type = "variant"

        variant_2.paths.repository = "repo_2"
        variant_2.paths.packages = "pkgs_2"
        variant_2.paths.source_repository = "src repo 2"
        variant_2.paths.source_packages = "src pkgs 2"
        variant_2.paths.debug_repository = "debug repo 2"
        variant_2.paths.debug_packages = "debug pkgs 2"
        variant_2.paths.identity = "cert2.pem"

        ti.variants.add(variant_2)

        ti.dump(self.ini_path, main_variant='BaseOS')
        with open(
                self.ini_path, 'r'
        ) as treeinfo_1, open(
            os.path.join(DIR, "treeinfo/multivariants_treeinfo")
        ) as treeinfo_2:
            treeinfo_1_lines = treeinfo_1.readlines()
            treeinfo_2_lines = treeinfo_2.readlines()
        self.assertEqual(
            treeinfo_1_lines,
            treeinfo_2_lines,
        )

    def test_f20(self):
        ti = TreeInfo()
        ti.load(os.path.join(DIR, "treeinfo/fedora-20-Fedora.x86_64"))

        # product
        self.assertEqual(ti.release.name, "Fedora")
        self.assertEqual(ti.release.short, "Fedora")
        self.assertEqual(ti.release.version, "20")

        # tree
        self.assertEqual(ti.tree.arch, "x86_64")
        # XXX: converts float to int
        self.assertEqual(ti.tree.build_timestamp, 1386857206)

        # variants
        self.assertEqual(len(ti.variants), 1)

        # variant: Fedora
        var = ti.variants["Fedora"]
        self.assertEqual(var.id, "Fedora")
        self.assertEqual(var.uid, "Fedora")
        self.assertEqual(var.name, "Fedora")
        self.assertEqual(var.type, "variant")

        self.assertEqual(var.paths.packages, "Packages")
        self.assertEqual(var.paths.repository, ".")

        # stage2
        self.assertEqual(ti.stage2.mainimage, "LiveOS/squashfs.img")
        self.assertEqual(ti.stage2.instimage, None)

        # images
        expected_images = {
            "kernel": "images/pxeboot/vmlinuz",
            "initrd": "images/pxeboot/initrd.img",
            "upgrade": "images/pxeboot/upgrade.img",
            "boot.iso": "images/boot.iso",
        }
        self.assertEqual(ti.images.images["x86_64"], expected_images)

        expected_images = {
            "kernel": "images/pxeboot/vmlinuz",
            "initrd": "images/pxeboot/initrd.img",
            "upgrade": "images/pxeboot/upgrade.img",
        }
        self.assertEqual(ti.images.images["xen"], expected_images)

        # checksums
        expected_checksums = {
            "images/boot.iso": ("sha256", "376be7d4855ad6281cb139430606a782fd6189dcb01d7b61448e915802cc350f"),
            "images/efiboot.img": ("sha256", "3bcba2a9b45366ab3f6d82dbe512421ddcb693f3bcbd9e30cc57aa0fa13c7835"),
            "images/macboot.img": ("sha256", "698b3492534399e31fa1033f51f25b85d463e743f6a26322a9b117f9aac4fdf3"),
            "images/pxeboot/initrd.img": ("sha256", "d0a81824e3425b6871ec4896a66e891aed35e291c50dfa30b08f6fc6ab04ca8b"),
            "images/pxeboot/upgrade.img": ("sha256", "a274b8756290447950f1e48cff9d9d6fd1144579ad98ed9f91929ff9ac1bbfa9"),
            "images/pxeboot/vmlinuz": ("sha256", "d3a2fbfcf08ac76dfb8135771380ec97ae3129b4e623891adb21bb1cd8ba59f6"),
            "repodata/repomd.xml": ("sha256", "108b4102829c0839c7712832577fe7da24f0a9491f4dc25d4145efe6aced2ebf"),
        }
        self.assertEqual(ti.checksums.checksums, expected_checksums)

        self._test_identity(ti)

    def test_f21_server(self):
        ti = TreeInfo()
        ti.load(os.path.join(DIR, "treeinfo/fedora-21-Alpha-Server.x86_64"))

        # product
        self.assertEqual(ti.release.name, "Fedora")
        self.assertEqual(ti.release.short, "Fedora")
        self.assertEqual(ti.release.version, "21")

        # tree
        self.assertEqual(ti.tree.arch, "x86_64")
        # XXX: converts float to int
        self.assertEqual(ti.tree.build_timestamp, 1410862874)

        # variants
        self.assertEqual(len(ti.variants), 1)

        # variant: Server
        var = ti.variants["Server"]
        self.assertEqual(var.id, "Server")
        self.assertEqual(var.uid, "Server")
        self.assertEqual(var.name, "Server")
        self.assertEqual(var.type, "variant")

        self.assertEqual(var.paths.packages, "Packages")
        self.assertEqual(var.paths.repository, ".")

        # stage2
        self.assertEqual(ti.stage2.mainimage, "LiveOS/squashfs.img")
        self.assertEqual(ti.stage2.instimage, None)

        # images
        expected_images = {
            "kernel": "images/pxeboot/vmlinuz",
            "initrd": "images/pxeboot/initrd.img",
            "upgrade": "images/pxeboot/upgrade.img",
            "boot.iso": "images/boot.iso",
        }
        self.assertEqual(ti.images.images["x86_64"], expected_images)

        expected_images = {
            "kernel": "images/pxeboot/vmlinuz",
            "initrd": "images/pxeboot/initrd.img",
            "upgrade": "images/pxeboot/upgrade.img",
        }
        self.assertEqual(ti.images.images["xen"], expected_images)

        # checksums
        expected_checksums = {
            "images/boot.iso": ("sha256", "e9c8b207d25c4af1a36c43a4cc3bf27dd2aefa9757eac63a8147e12e415f45f3"),
            "images/efiboot.img": ("sha256", "0655a92312272a2ee929f579c7ac5086c0ab75b7453a0293a38502d69a8335d3"),
            "images/macboot.img": ("sha256", "c25721c2e69ea82eedd78107baf69fc0d2900c5a23d0b689140edc2b372393f9"),
            "images/pxeboot/initrd.img": ("sha256", "b6cffe60149c0396b3413bf3f73c3a1aa3090048302daeeeb8830911d903aa2f"),
            "images/pxeboot/upgrade.img": ("sha256", "260ab3a63fb4ef1f0427a6b46d494c638760e0bb4e7e9f58295d0cf4e77886fc"),
            "images/pxeboot/vmlinuz": ("sha256", "974cbed883608046bacfc7a4f232320750150c2821edcd4650fbbe709a6c1d3d"),
            "repodata/repomd.xml": ("sha256", "1799b6652f287c73e1f1107ef5efe73a0714aaf34e8e9b81a08d3f741f5dc178"),
        }
        self.assertEqual(ti.checksums.checksums, expected_checksums)

        self._test_identity(ti)

    def test_read_treeinfo(self):
        for i in os.listdir(self.treeinfo_path):
            if i in ("fedora-8-Everything.x86_64", "fedora-8-Everything.ppc", "fedora-8-Everything.i386"):
                # version == "development" -> can't read correctly
                continue
            if "fedora" not in i:
                # Not a Fedora file
                continue
            path = os.path.join(self.treeinfo_path, i)
            ti = TreeInfo()
            ti.load(path)
            self.assertEqual(ti.release.short, "Fedora")
            self.assertEqual(ti.release.name, "Fedora")
            self.assertEqual(ti.release.version, str(int(ti.release.version)))

    def test_read_RHEL_treeinfo(self):
        for i in os.listdir(self.treeinfo_path):
            if "RHEL" not in i:
                continue
            if "optional" in i:
                continue
            path = os.path.join(self.treeinfo_path, i)
            ti = TreeInfo()
            ti.load(path)
            self.assertEqual(ti.release.short, "RHEL")
            self.assertEqual(ti.release.name, "Red Hat Enterprise Linux")
            self.assertEqual(ti.release.version, str(ti.release.version))

            # variants
            self.assertEqual(len(ti.variants), 2)

            # variant: BaseOS
            var = ti.variants["BaseOS"]
            self.assertEqual(var.id, "BaseOS")
            self.assertEqual(var.uid, "BaseOS")
            self.assertEqual(var.name, "BaseOS")
            self.assertEqual(var.type, "variant")

            self.assertEqual(var.paths.packages, "Packages")
            self.assertEqual(var.paths.repository, ".")

            # variant: AppStream
            var = ti.variants["AppStream"]
            self.assertEqual(var.id, "AppStream")
            self.assertEqual(var.uid, "AppStream")
            self.assertEqual(var.name, "AppStream")
            self.assertEqual(var.type, "variant")

            self.assertEqual(var.paths.packages, "Packages")

    def test_read_RHEL_Server_optional_treeinfo(self):
        path = os.path.join(self.treeinfo_path, "RHEL-7-Server-optional.x86_64")
        ti = TreeInfo()
        ti.load(path)

        var = ti.variants["Server-optional"]
        self.assertEqual(var.id, "optional")
        self.assertEqual(var.uid, "Server-optional")
        self.assertEqual(var.name, "optional")
        self.assertEqual(var.type, "optional")
        self.assertEqual(var.paths.packages, "Packages")
        self.assertEqual(var.paths.repository, ".")

    def test_treeinfo_compute_checksum(self):
        tmp_file = os.path.join(self.tmp_dir, "file")
        with open(tmp_file, "w") as f:
            f.write("test")
        expected_checksum = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
        ti = TreeInfo()
        ti.checksums.add("file", "sha256", None, self.tmp_dir)
        self.assertEqual(ti.checksums.checksums["file"], ["sha256", expected_checksum])

    def test_parse_opensuse_treeinfo(self):
        ti = TreeInfo()
        ti.load(os.path.join(self.treeinfo_path, "opensuse"))
        self.assertEqual(ti.release.name, "openSUSE Leap")
        self.assertEqual(ti.release.short, "openSUSE Leap")
        self.assertEqual(ti.release.version, "15.1")
        self.assertEqual(ti.variants.variants, {})
        self.assertEqual(ti.tree.arch, "x86_64")
        self.assertEqual(ti.tree.platforms, set(["x86_64", "xen"]))
        self.assertEqual(
            ti.images.images,
            {
                "x86_64": {
                    "initrd": "boot/x86_64/loader/initrd",
                    "kernel": "boot/x86_64/loader/linux",
                },
                "xen": {
                    "initrd": "boot/x86_64/loader/initrd",
                    "kernel": "boot/x86_64/loader/linux",
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
