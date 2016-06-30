#!/usr/bin/env python
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

from productmd.compose import Compose   # noqa


class TestCompose(unittest.TestCase):

    def test_opening_wrong_dir_gives_descriptive_error(self):
        compose = Compose('/a/b/c')
        try:
            compose.rpms
            self.fail('Accessing the attribute must raise exception')
        except RuntimeError as e:
            self.assertEqual(str(e), r"Failed to load metadata from /a/b/c")
        except:
            self.fail('Expected to get RuntimeError')


if __name__ == "__main__":
    unittest.main()
