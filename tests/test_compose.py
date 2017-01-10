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

import productmd.common
from six import StringIO
from six.moves.urllib.error import HTTPError


class TestCompose(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestCompose, self).__init__(*args, **kwargs)
        self.compose_path = os.path.join(DIR, "compose")

    def test_read_composeinfo(self):
        compose = Compose(self.compose_path)
        compose.info

        # try to access a variant and addon
        variant = compose.info["Foo"]
        variant = compose.info["Foo-Bar"]

    def test_opening_wrong_dir_gives_descriptive_error(self):
        compose = Compose('/a/b/c')
        try:
            compose.rpms
            self.fail('Accessing the attribute must raise exception')
        except RuntimeError as e:
            self.assertEqual(str(e), r"Failed to load metadata from /a/b/c")
        except:
            self.fail('Expected to get RuntimeError')

    def test_opening_http_succeeds(self):
        def mock_urlopen(url, context=None):
            """ Return an on-disk JSON file's contents for a given url. """
            filename = os.path.basename(url)
            if not filename.endswith('.json'):
                # This is not parsed; it just needs to be any 200 OK response.
                return StringIO()
            try:
                f = open(os.path.join(self.compose_path, "compose", "metadata", filename), 'r')
            except IOError as e:
                raise HTTPError(404, e)
            return f

        orig_urlopen = productmd.common.six.moves.urllib.request.urlopen
        try:
            productmd.common.six.moves.urllib.request.urlopen = mock_urlopen
            compose = Compose('http://example.noexist/path/to/mycompose')
            self.assertEqual('MYPRODUCT', compose.info.release.short)
        finally:
            productmd.common.six.moves.urllib.request.urlopen = orig_urlopen


class TestLegacyCompose(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestLegacyCompose, self).__init__(*args, **kwargs)
        self.compose_path = os.path.join(DIR, "compose-legacy")

    def test_read_composeinfo(self):
        compose = Compose(self.compose_path)
        compose.info

        # try to access a variant and addon
        variant = compose.info["Foo"]
        variant = compose.info["Foo-Bar"]

if __name__ == "__main__":
    unittest.main()
