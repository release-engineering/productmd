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


"""
This module provides Compose class that provides easy access
to ComposeInfo, Rpms and Images in compose metadata.

Example::

  import productmd.compose
  compose = productmd.compose.Compose("/path/to/compose")

  # then you can access compose metadata via following properties:
  compose.info
  compose.images
  compose.rpms
"""


import os

import productmd.composeinfo
import productmd.images
import productmd.rpms


__all__ = (
    "Compose",
)


class Compose(object):
    """
    This class provides easy access to compose metadata.
    """

    def __init__(self, compose_path):
        self.compose_path = compose_path
        compose_path = os.path.join(compose_path, "compose")
        if os.path.isdir(compose_path):
            self.compose_path = compose_path

        self._composeinfo = None
        self._images = None
        self._rpms = None

    def _find_metadata_file(self, paths):
        for i in paths:
            path = os.path.join(self.compose_path, i)
            if os.path.exists(path):
                return path
        return None

    @property
    def info(self):
        """(:class:`productmd.composeinfo.ComposeInfo`) -- Compose metadata"""
        if self._composeinfo is not None:
            return self._composeinfo

        composeinfo = productmd.composeinfo.ComposeInfo()
        paths = [
            "metadata/composeinfo.json",
        ]
        path = self._find_metadata_file(paths)
        composeinfo.load(path)
        self._composeinfo = composeinfo
        return self._composeinfo

    @property
    def images(self):
        """(:class:`productmd.images.Images`) -- Compose images metadata"""
        if self._images is not None:
            return self._images

        images = productmd.images.Images()
        paths = [
            "metadata/images.json",
            "metadata/image-manifest.json",
        ]
        path = self._find_metadata_file(paths)
        images.load(path)
        self._images = images
        return self._images

    @property
    def rpms(self):
        """(:class:`productmd.rpms.Rpms`) -- Compose RPMs metadata"""
        if self._rpms is not None:
            return self._rpms

        rpms = productmd.rpms.Rpms()
        paths = [
            "metadata/rpms.json",
            "metadata/rpm-manifest.json",
        ]
        path = self._find_metadata_file(paths)
        rpms.load(path)
        self._rpms = rpms
        return self._rpms
