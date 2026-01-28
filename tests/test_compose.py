#!/usr/bin/env python3

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


import pytest
from unittest import mock

import os
import urllib.request

from productmd.compose import Compose

from io import StringIO
from urllib.error import HTTPError

DIR = os.path.dirname(__file__)


@pytest.mark.parametrize("fixture", ["compose", "compose-legacy"])
def test_read_composeinfo(fixture):
    compose = Compose(os.path.join(DIR, fixture))
    assert compose.info is not None

    # try to access a variant and addon
    assert compose.info["Foo"] is not None
    assert compose.info["Foo-Bar"] is not None


def test_opening_wrong_dir_gives_descriptive_error():
    compose = Compose('/a/b/c')
    with pytest.raises(RuntimeError, match="Failed to load metadata from /a/b/c"):
        compose.rpms


def test_opening_http_succeeds():
    def mock_urlopen(url, context=None):
        """ Return an on-disk JSON file's contents for a given url. """
        # Handle both string URLs and Request objects
        if isinstance(url, urllib.request.Request):
            url = url.full_url
        filename = os.path.basename(url)
        if not filename.endswith('.json'):
            # This is not parsed; it just needs to be any 200 OK response.
            return StringIO()
        try:
            f = open(os.path.join(DIR, "compose", "compose", "metadata", filename), 'r')
        except IOError as e:
            raise HTTPError(404, e)
        return f

    with mock.patch("urllib.request.urlopen", new=mock_urlopen):
        compose = Compose('http://example.noexist/path/to/mycompose')
        assert 'MYPRODUCT' == compose.info.release.short
