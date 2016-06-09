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

from productmd.rpms import Rpms  # noqa


class TestRpms(unittest.TestCase):
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

    def _test_identity(self, rm):
        first = os.path.join(self.tmp_dir, "first")
        second = os.path.join(self.tmp_dir, "second")

        # write original file
        rm.dump(first)

        # read file and write it back
        rm = Rpms()
        rm.load(first)
        rm.dump(second)

        # check if first and second files are identical
        self.assertSameFiles(first, second)

    def test_fedora_20(self):
        rm = Rpms()
        rm.header.version = "1.0"
        rm.compose.id = "Fedora-20-20131212.0"
        rm.compose.type = "production"
        rm.compose.date = "20131212"
        rm.compose.respin = 0

        # binary RPMs
        rm.add(
            "Fedora",
            "x86_64",
            "glibc-0:2.18-11.fc20.x86_64.rpm",
            path="Fedora/x86_64/os/Packages/g/glibc-2.18-11.fc20.x86_64.rpm",
            sigkey="246110c1",
            category="binary",
            srpm_nevra="glibc-0:2.18-11.fc20.src.rpm",
        )
        rm.add(
            "Fedora",
            "x86_64",
            "glibc-common-0:2.18-11.fc20.x86_64.rpm",
            path="Fedora/x86_64/os/Packages/g/glibc-common-2.18-11.fc20.x86_64.rpm",
            sigkey="246110c1",
            category="binary",
            srpm_nevra="glibc-0:2.18-11.fc20.src.rpm",
        )

        # source RPM
        rm.add(
            "Fedora",
            "x86_64",
            "glibc-0:2.18-11.fc20.src.rpm",
            path="Fedora/source/SRPMS/g/glibc-2.18-11.fc20.x86_64.rpm",
            sigkey="246110c1",
            category="source",
        )

        self._test_identity(rm)

        # 1 arch
        self.assertEqual(len(rm["Fedora"]), 1)

        # 1 SRPM
        self.assertEqual(len(rm["Fedora"]["x86_64"]), 1)

        # 3 RPMs (including 1 SRPM)
        self.assertEqual(len(rm["Fedora"]["x86_64"]["glibc-0:2.18-11.fc20.src"]), 3)

    def test_forbidden_src_arch(self):
        """
        Test: ValueError("Source arch is not allowed. Map source files under binary arches.")
        """
        rm = Rpms()
        self.assertRaises(
            ValueError,
            rm.add,
            "Fedora",
            "src",
            "glibc-0:2.18-11.fc20.src.rpm",
            path="Fedora/source/SRPMS/g/glibc-2.18-11.fc20.x86_64.rpm",
            sigkey="246110c1",
            category="source",
        )


if __name__ == "__main__":
    unittest.main()
