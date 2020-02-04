# -*- coding: utf-8 -*-

# Copyright (C) 2019  Red Hat, Inc.
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
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, see <https://gnu.org/licenses/>.


import unittest

import json
import os
import sys
import tempfile
import shutil

from six import StringIO

DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(DIR, ".."))

from productmd.extra_files import ExtraFiles    # noqa


class TestExtraFiles(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def assertSameFiles(self, path1, path2):
        self.assertEqual(os.path.getsize(path1), os.path.getsize(path2))
        with open(path1, "r") as file1:
            with open(path2, "r") as file2:
                self.assertEqual(file1.read(), file2.read())

    def _test_identity(self, modules):
        first = os.path.join(self.tmp_dir, "first")
        second = os.path.join(self.tmp_dir, "second")

        # write original file
        modules.dump(first)

        # read file and write it back
        modules = ExtraFiles()
        modules.load(first)
        modules.dump(second)

        # check if first and second files are identical
        self.assertSameFiles(first, second)

    def test_bad_checksums(self):
        metadata = ExtraFiles()
        self.assertRaises(
            TypeError,
            metadata.add,
            "Everything",
            "x86_64",
            "path/to/file",
            size=1,
            checksums="no",
        )

    def test_bad_variant(self):
        metadata = ExtraFiles()
        self.assertRaises(
            ValueError, metadata.add, "", "x86_64", "path/to/file", size=1, checksums={}
        )

    def test_bad_arch(self):
        metadata = ExtraFiles()
        self.assertRaises(
            ValueError,
            metadata.add,
            "Everything",
            "foobar",
            "path/to/file",
            size=1,
            checksums={},
        )

    def test_bad_path(self):
        metadata = ExtraFiles()
        self.assertRaises(
            ValueError, metadata.add, "Everything", "foobar", "", size=1, checksums={}
        )

    def test_absolute_path(self):
        metadata = ExtraFiles()
        self.assertRaises(
            ValueError,
            metadata.add,
            "Everything",
            "foobar",
            "/path",
            size=1,
            checksums={},
        )

    def test_fedora_20(self):
        metadata = ExtraFiles()
        metadata.header.version = "1.0"
        metadata.compose.id = "Fedora-20-20131212.0"
        metadata.compose.type = "production"
        metadata.compose.date = "20131212"
        metadata.compose.respin = 0

        metadata.add(
            "Everything",
            "x86_64",
            "compose/Everything/x86_64/os/GPL",
            size=123,
            checksums={"md5": "abcde", "sha512": "a1b2c3"},
        )

        self._test_identity(metadata)

    def test_partial_dump(self):
        metadata = ExtraFiles()
        metadata.header.version = "1.0"
        metadata.compose.id = "Fedora-20-20131212.0"
        metadata.compose.type = "production"
        metadata.compose.date = "20131212"
        metadata.compose.respin = 0

        metadata.add(
            "Everything",
            "x86_64",
            "compose/Everything/x86_64/os/GPL",
            size=123,
            checksums={"md5": "abcde", "sha512": "a1b2c3"},
        )

        out = StringIO()
        metadata.dump_for_tree(out, "Everything", "x86_64", "compose/Everything/x86_64/os")
        self.assertEqual(
            json.loads(out.getvalue()),
            {
                "header": {"version": "1.0"},
                "data": [
                    {
                        "file": "GPL",
                        "size": 123,
                        "checksums": {"md5": "abcde", "sha512": "a1b2c3"},
                    },
                ],
            },
        )

    def test_partial_dump_in_deleted_directory(self):
        os.chdir(self.tmp_dir)
        shutil.rmtree(self.tmp_dir)

        metadata = ExtraFiles()
        metadata.header.version = "1.0"
        metadata.compose.id = "Fedora-20-20131212.0"
        metadata.compose.type = "production"
        metadata.compose.date = "20131212"
        metadata.compose.respin = 0

        metadata.add(
            "Everything",
            "x86_64",
            "compose/Everything/x86_64/os/GPL",
            size=123,
            checksums={"md5": "abcde", "sha512": "a1b2c3"},
        )

        out = StringIO()
        metadata.dump_for_tree(out, "Everything", "x86_64", "compose/Everything/x86_64/os")
