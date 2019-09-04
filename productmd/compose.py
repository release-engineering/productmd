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
to ComposeInfo, Rpms, Modules and Images in compose metadata.

Example::

  import productmd.compose
  compose = productmd.compose.Compose("/path/to/compose")

  # then you can access compose metadata via following properties:
  compose.info
  compose.images
  compose.rpms
  compose.modules
"""


import os

import productmd.composeinfo
import productmd.images
import productmd.rpms
import productmd.modules
from productmd.common import _file_exists


__all__ = (
    "Compose",
)


class Compose(object):
    """
    This class provides easy access to compose metadata.

    :param compose_path:        Path to a compose. HTTP(s) URL is also accepted.
    :type  compose_path:        str
    """

    def __init__(self, compose_path):
        # example: MYPRODUCT-1.0-YYYYMMDD.0/metadata
        self.compose_path = compose_path

        # example: MYPRODUCT-1.0-YYYYMMDD.0/compose/metadata (preferred location)
        path = os.path.join(compose_path, "compose")
        if _file_exists(path):
            self.compose_path = path

        elif "://" not in compose_path and os.path.exists(compose_path):
            # Scan all subdirs under compose_path for 'metadata'. Doesn't work over HTTP.
            # example: MYPRODUCT-1.0-YYYYMMDD.0/1.0/metadata (legacy location)
            for i in os.listdir(compose_path):
                path = os.path.join(compose_path, i)
                metadata_path = os.path.join(path, "metadata")
                if _file_exists(metadata_path):
                    self.compose_path = path
                    break

        self._composeinfo = None
        self._images = None
        self._rpms = None
        self._modules = None

    def _find_metadata_file(self, paths):
        for i in paths:
            path = os.path.join(self.compose_path, i)
            if _file_exists(path):
                return path
        raise RuntimeError('Failed to load metadata from %s' % self.compose_path)

    @property
    def info(self):
        """(:class:`productmd.composeinfo.ComposeInfo`) -- Compose metadata"""
        if self._composeinfo is not None:
            return self._composeinfo

        paths = [
            "metadata/composeinfo.json",
        ]
        self._composeinfo = self._load_metadata(paths, productmd.composeinfo.ComposeInfo)
        return self._composeinfo

    @property
    def images(self):
        """(:class:`productmd.images.Images`) -- Compose images metadata"""
        if self._images is not None:
            return self._images

        paths = [
            "metadata/images.json",
            "metadata/image-manifest.json",
        ]
        self._images = self._load_metadata(paths, productmd.images.Images)
        return self._images

    @property
    def rpms(self):
        """(:class:`productmd.rpms.Rpms`) -- Compose RPMs metadata"""
        if self._rpms is not None:
            return self._rpms

        paths = [
            "metadata/rpms.json",
            "metadata/rpm-manifest.json",
        ]
        self._rpms = self._load_metadata(paths, productmd.rpms.Rpms)
        return self._rpms

    @property
    def modules(self):
        """(:class:`productmd.modules.Modules`) -- Compose Modules metadata"""
        if self._modules is not None:
            return self._modules

        paths = [
            "metadata/modules.json",
        ]
        self._modules = self._load_metadata(paths, productmd.modules.Modules)
        return self._modules

    def _load_metadata(self, paths, cls):
        path = self._find_metadata_file(paths)
        obj = cls()
        try:
            obj.load(path)
        except ValueError as exc:
            raise RuntimeError('%s can not be deserialized: %s.' % (path, exc))
        return obj
