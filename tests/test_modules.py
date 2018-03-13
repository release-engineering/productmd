#!/usr/bin/python
# -*- coding: utf-8 -*-


# Copyright (C) 2018  Red Hat, Inc.
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

from productmd.modules import Modules  # noqa


class TestModules(unittest.TestCase):
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

    def _test_identity(self, modules):
        first = os.path.join(self.tmp_dir, "first")
        second = os.path.join(self.tmp_dir, "second")

        # write original file
        modules.dump(first)

        # read file and write it back
        modules = Modules()
        modules.load(first)
        modules.dump(second)

        # check if first and second files are identical
        self.assertSameFiles(first, second)

    def test_fedora_20(self):
        my_version = "1.0"

        modules = Modules()
        modules.header.version = my_version
        modules.compose.id = "Fedora-20-20131212.0"
        modules.compose.type = "production"
        modules.compose.date = "20131212"
        modules.compose.respin = 0

        modules.modules = {
            "Fedora": {
                "x86_64": {
                    "ant:1.10:20180301142136:95f078a1": {
                        "metadata": {
                            "uid": "ant:1.10:20180301142136:95f078a1",
                            "name": "ant",
                            "stream": "1.10",
                            "version": "20180301142136",
                            "context": "95f078a1",
                            "koji_tag": "module-66c333b434067fb3a",
                        },
                        "modulemd_path": "Components/x86_64/os/repodata/8466dbe8894b6e136237a2a8b70dadcf8d3742fea93884c-modules.yaml.gz",
                        "rpms": [],
                    }
                }
            }
        }

        self._test_identity(modules)
        self.assertNotEqual(modules.header.version, my_version)  # check whether field was replaced by newer version

    def test_compare(self):
        """
        two ways creating metadata and its results comparison
        """
        modules1 = Modules()
        modules1.header.version = "1.0"
        modules1.compose.id = "Fedora-20-20131212.0"
        modules1.compose.type = "production"
        modules1.compose.date = "20131212"
        modules1.compose.respin = 0

        modules1.add(
            variant="FedoraX",
            arch="x86_64",
            uid="testmodule:1.10:20180301142136:95f078a1",
            koji_tag="module-66c333b434067fb3a",
            modulemd_path="FedoraX/x86_64/os/repodata/8466dbe8894b6e136237a2a8b70dadcf8d3-modules.yaml.gz",
            category="binary",
            rpms=["pkg1", "pkg2"],
        )

        modules2 = Modules()
        modules2.header.version = "1.0"
        modules2.compose.id = "Fedora-20-20131212.0"
        modules2.compose.type = "production"
        modules2.compose.date = "20131212"
        modules2.compose.respin = 0

        modules2.modules = {
            "FedoraX": {
                "x86_64": {
                    "testmodule:1.10:20180301142136:95f078a1": {
                        "metadata": {
                            "uid": "testmodule:1.10:20180301142136:95f078a1",
                            "name": "testmodule",
                            "stream": "1.10",
                            "version": "20180301142136",
                            "context": "95f078a1",
                            "koji_tag": "module-66c333b434067fb3a",
                        },
                        "modulemd_path": {"binary": "FedoraX/x86_64/os/repodata/8466dbe8894b6e136237a2a8b70dadcf8d3-modules.yaml.gz"},
                        "rpms": ["pkg1", "pkg2"],
                    }
                }
            }
        }

        third = os.path.join(self.tmp_dir, "third")
        fourth = os.path.join(self.tmp_dir, "fourth")
        modules1.dump(third)
        modules2.dump(fourth)
        self.assertSameFiles(third, fourth)


if __name__ == "__main__":
    unittest.main()
