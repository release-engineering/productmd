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
This module provides classes for manipulating .discinfo files.
.discinfo files can be found on Fedora installation media and
provide media information to Anaconda installer.
"""


import time

import productmd.common


__all__ = (
    "DiscInfo",
)


class DiscInfo(productmd.common.MetadataBase):
    """
    This class manipulates .discinfo files used by Anaconda installer.
    """

    def __init__(self):
        super(DiscInfo, self).__init__()
        self.timestamp = None           #: Timestamp in float format
        self.description = None         #: Release description, for example: Fedora 20
        self.arch = None                #: Media architecture, for example: x86_64
        self.disc_numbers = []          #: List with disc numbers or ["ALL"]

    def _validate_timestamp(self, value=None):
        value = value or self.timestamp
        self._assert_not_blank("timestamp")
        self._assert_type("timestamp", [float])

    def _validate_description(self):
        self._assert_not_blank("description")
        self._assert_type("description", [str])

    def _validate_arch(self):
        self._assert_not_blank("arch")
        self._assert_type("arch", [str])

    def _validate_disc_numbers(self):
        self._assert_not_blank("disc_numbers")
        self._assert_type("disc_numbers", [list])
        if self.disc_numbers == ["ALL"]:
            return
        # TODO: check if disc numbers are integers

    def _get_parser(self):
        return []

    def parse_file(self, f):
        # parse file, return parser or dict with data
        f.seek(0)
        parser = [i.strip() for i in f.readlines()]
        return parser

    def build_file(self, parser, f):
        # build file from parser or dict with data
        f.write("\n".join(parser))

    def deserialize(self, parser):
        lines = parser
        self.timestamp = float(lines[0].strip())
        self.description = lines[1].strip().strip("\"\'")
        self.arch = lines[2].strip()
        disc_numbers = None
        if len(parser) >= 4:
            disc_numbers = lines[3].strip()
        if not disc_numbers or disc_numbers == "ALL":
            self.disc_numbers = ["ALL"]
        else:
            self.disc_numbers = [int(i) for i in disc_numbers.split(",")]
        self.validate()

    def serialize(self, parser):
        self.validate()
        lines = parser
        lines.append(str(self.timestamp).strip())
        lines.append(self.description.strip())
        lines.append(self.arch.strip())
        if self.disc_numbers == ["ALL"]:
            lines.append("ALL")
        else:
            lines.append(",".join([str(i) for i in self.disc_numbers]))

    def now(self):
        """Shortcut for setting timestamp to now()."""
        self.timestamp = time.time()
