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

from productmd.discinfo import DiscInfo  # noqa


class TestDiscInfo(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestDiscInfo, self).__init__(*args, **kwargs)
        self.discinfo_path = os.path.join(DIR, "discinfo")

    def setUp(self):
        self.maxDiff = None
        self.tmp_dir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp_dir, "discinfo")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_empty(self):
        di = DiscInfo()
        self.assertRaises(ValueError, di.dump, self.path)

    def test_invalid_values(self):
        di = DiscInfo()
        di.timestamp = "foo"
        di.description = "Fedora 21"
        di.arch = "x86_64"
        di.disc_numbers = ["ALL"]
        self.assertRaises(TypeError, di.dumps)

    def assertSameFiles(self, path1, path2):
        self.assertEqual(os.path.getsize(path1), os.path.getsize(path2))
        with open(path1, "r") as file1:
            with open(path2, "r") as file2:
                self.assertEqual(file1.read(), file2.read())

    def _test_identity(self, di):
        first = os.path.join(self.tmp_dir, "first")
        second = os.path.join(self.tmp_dir, "second")

        # write original file
        di.dump(first)

        # read file and write it back
        di = DiscInfo()
        di.load(first)
        di.dump(second)

        # check if first and second files are identical
        self.assertSameFiles(first, second)

    def test_all(self):
        di = DiscInfo()
        di.now()
        di.description = "Fedora 20"
        di.arch = "x86_64"
        di.disc_numbers = ["ALL"]
        di.dump(self.path)

        self._test_identity(di)

    def test_disc_numbers(self):
        di = DiscInfo()
        di.timestamp = 1386856788.124593
        di.description = "Fedora 20"
        di.arch = "x86_64"
        di.disc_numbers = [1, "2", 3]
        di.dump(self.path)

        self._test_identity(di)

    def test_parse(self):
        lines = [
            "1386856788.124593",
            "Fedora 20",
            "x86_64",
            "ALL",
        ]
        di = DiscInfo()
        di.loads("\n".join(lines))
        self.assertEqual(di.timestamp, 1386856788.124593)
        self.assertEqual(di.description, "Fedora 20")
        self.assertEqual(di.arch, "x86_64")
        self.assertEqual(di.disc_numbers, ["ALL"])

    def test_parse_disc_numbers(self):
        lines = [
            "1386856788.124593",
            "Fedora 20",
            "x86_64",
            "1,2, 3,4 ",
        ]
        di = DiscInfo()
        di.loads("\n".join(lines))
        self.assertEqual(di.timestamp, 1386856788.124593)
        self.assertEqual(di.description, "Fedora 20")
        self.assertEqual(di.arch, "x86_64")
        self.assertEqual(di.disc_numbers, [1, 2, 3, 4])

    def test_parse_no_disc_numbers(self):
        lines = [
            "1386856788.124593",
            "Fedora 20",
            "x86_64",
        ]
        di = DiscInfo()
        di.loads("\n".join(lines))
        self.assertEqual(di.timestamp, 1386856788.124593)
        self.assertEqual(di.description, "Fedora 20")
        self.assertEqual(di.arch, "x86_64")
        self.assertEqual(di.disc_numbers, ["ALL"])

    def test_read_discinfo(self):
        for i in os.listdir(self.discinfo_path):
            path = os.path.join(self.discinfo_path, i)
            di = DiscInfo()
            di.load(path)


if __name__ == "__main__":
    unittest.main()
