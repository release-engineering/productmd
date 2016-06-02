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

from productmd.composeinfo import ComposeInfo, Variant, Release  # noqa


class TestComposeInfo(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestComposeInfo, self).__init__(*args, **kwargs)
        self.treeinfo_path = os.path.join(DIR, "treeinfo")

    def setUp(self):
        self.maxDiff = None
        self.tmp_dir = tempfile.mkdtemp()
        self.ci_path = os.path.join(self.tmp_dir, "composeinfo")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def assertSameFiles(self, path1, path2):
        self.assertEqual(os.path.getsize(path1), os.path.getsize(path2))
        file1 = open(path1, "r")
        file2 = open(path2, "r")
        self.assertEqual(file1.read(), file2.read())
        file1.close()
        file2.close()

    def _test_identity(self, ci):
        first = os.path.join(self.tmp_dir, "first")
        second = os.path.join(self.tmp_dir, "second")

        # write original file
        ci.dump(first)

        # read file and write it back
        ci = ComposeInfo()
        ci.load(first)
        ci.dump(second)

        # check if first and second files are identical
        self.assertSameFiles(first, second)

    def test_create(self):
        ci = ComposeInfo()
        ci.release.name = "Fedora"
        ci.release.short = "F"
        ci.release.version = "22"
        ci.release.type = "ga"

        ci.compose.id = "F-22-20150522.0"
        ci.compose.type = "production"
        ci.compose.date = "20150522"
        ci.compose.respin = 0

        variant = Variant(ci)
        variant.id = "Server"
        variant.uid = "Server"
        variant.name = "Server"
        variant.type = "variant"
        variant.arches = ["armhfp", "i386", "x86_64"]

        ci.variants.add(variant)

        ci.dump(self.ci_path)
        self._test_identity(ci)
        return ci

    def test_is_ga(self):
        ci = self.test_create()
        self.assertEqual(ci.compose.final, False)
        self.assertEqual(ci.compose.is_ga, False)
        ci.dump(self.ci_path)

        ci.compose.final = True
        self.assertEqual(ci.compose.final, True)
        self.assertEqual(ci.compose.is_ga, False)
        ci.dump(self.ci_path)

        ci.compose.label = "Beta-2.1"
        self.assertEqual(ci.compose.final, True)
        self.assertEqual(ci.compose.is_ga, False)
        ci.dump(self.ci_path)

        ci.compose.label = "RC-2.1"
        self.assertEqual(ci.compose.final, True)
        self.assertEqual(ci.compose.is_ga, True)
        ci.dump(self.ci_path)

        # GA is not a valid label; GA is the last RC that is marked as final
        ci.compose.label = "GA"
        self.assertRaises(ValueError, ci.dump, self.ci_path)

    def test_release_non_numeric_version(self):
        r = Release(None)
        r.name = "Fedora"
        r.short = "f"
        r.version = "Rawhide"
        r.type = "ga"

        r.validate()

    def test_create_variants_with_dash(self):
        ci = ComposeInfo()
        ci.release.name = "Fedora"
        ci.release.short = "F"
        ci.release.version = "22"
        ci.release.type = "ga"

        ci.compose.id = "F-22-20150522.0"
        ci.compose.type = "production"
        ci.compose.date = "20150522"
        ci.compose.respin = 0

        # 2 Tools variants: one for Server, one for Workstation
        # but parent variants are not part of the compose
        variant = Variant(ci)
        variant.id = "ServerTools"
        variant.uid = "Server-Tools"
        variant.name = "Tools"
        variant.type = "variant"
        variant.arches = ["x86_64"]
        ci.variants.add(variant)
        ci.variants["Server-Tools"]

        variant = Variant(ci)
        variant.id = "WorkstationTools"
        variant.uid = "Workstation-Tools"
        variant.name = "Tools"
        variant.type = "variant"
        variant.arches = ["x86_64"]
        ci.variants.add(variant)
        ci.variants["Workstation-Tools"]

        ci.dump(self.ci_path)
        self._test_identity(ci)
        return ci


if __name__ == "__main__":
    unittest.main()
