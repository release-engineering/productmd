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

DIR = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(DIR, ".."))

from productmd.common import Header  # noqa


class TestHeader(unittest.TestCase):

    def test_version(self):
        hdr = Header(None, "productmd.header")

        # empty version
        hdr.version = None
        self.assertRaises(TypeError, hdr.validate)

        # invalid version
        hdr.version = "first"
        self.assertRaises(ValueError, hdr.validate)

        hdr.version = "1.alpha2"
        self.assertRaises(ValueError, hdr.validate)

        hdr.version = "1"
        self.assertRaises(ValueError, hdr.validate)

        # valid version
        hdr.version = "1.22"
        hdr.validate()

    def test_deserialize(self):
        hdr = Header(None, "productmd.header")
        data = {
            "header": {
                "type": "productmd.header",
                "version": "1.0",
            }
        }
        hdr.deserialize(data)
        self.assertEqual(hdr.version, "1.0")

    def test_serialize(self):
        hdr = Header(None, "productmd.header")
        hdr.version = "1.0"
        serialized_data = {}
        hdr.serialize(serialized_data)
        expected_data = {
            "header": {
                "type": "productmd.header",
                "version": "1.2",
            }
        }
        self.assertEqual(serialized_data, expected_data)


if __name__ == "__main__":
    unittest.main()
