# -*- coding: utf-8 -*-
# pylint: disable=super-on-old-class


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
This module provides base classes and common functions
used in other productmd modules.
"""


VERSION = (1, 0)


__all__ = (
    "MetadataBase",
    "Header",
    "VERSION",
)


import sys
import re
import json
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser as ConfigParser

import six


# HACK: dumped from rpmUtils.arch which is not available on python3
# one less dependency at least :)
RPM_ARCHES = [
    "aarch64", "alpha", "alphaev4", "alphaev45", "alphaev5", "alphaev56", "alphaev6", "alphaev67", "alphaev68",
    "alphaev7", "alphapca56", "amd64", "arm64", "armhfp", "armv5tejl", "armv5tel", "armv6hl", "armv6l", "armv7hl",
    "armv7hnl", "armv7l", "athlon", "geode", "i386", "i486", "i586", "i686", "ia32e", "ia64", "ppc", "ppc64",
    "ppc64iseries", "ppc64le", "ppc64p7", "ppc64pseries", "s390", "s390x", "sh3", "sh4", "sh4a",
    "sparc", "sparc64", "sparc64v", "sparcv8", "sparcv9", "sparcv9v", "x86_64",
    "src", "nosrc", "noarch",
]


RPM_NVRA_RE = re.compile(r"^(.*/)?(?P<name>.*)-((?P<epoch>\d+):)?(?P<version>.*)-(?P<release>.*)\.(?P<arch>.*)$")


def parse_nvra(nvra):
    if nvra.endswith(".rpm"):
        nvra = nvra[:-4]
    result = RPM_NVRA_RE.match(nvra).groupdict()
    result["epoch"] = result["epoch"] or 0
    result["epoch"] = int(result["epoch"])
    return result


class MetadataBase(object):
    def _assert_type(self, field, expected_types):
        value = getattr(self, field)
        for atype in expected_types:
            if isinstance(value, atype):
                return
        raise TypeError("%s: Field '%s' has invalid type: %s" % (self.__class__.__name__, field, type(value)))

    def _assert_value(self, field, expected_values):
        value = getattr(self, field)
        if value not in expected_values:
            raise ValueError("%s: Field '%s' has invalid value: %s" % (self.__class__.__name__, field, value))

    def _assert_not_blank(self, field):
        value = getattr(self, field)
        if not value:
            raise ValueError("%s: Field '%s' must not be blank" % (self.__class__.__name__, field))

    def _assert_matches_re(self, field, expected_patterns):
        value = getattr(self, field)
        for pattern in expected_patterns:
            if re.match(pattern, value):
                return
        raise ValueError("%s: Field '%s' has invalid value: %s. It does not match any provided REs: %s"
                         % (self.__class__.__name__, field, value, expected_patterns))

    def validate(self):
        """
        Validate attributes by running all self._validate_*() methods.

        :raises TypeError: if an attribute has invalid type
        :raises ValueError: if an attribute contains invalid value
        """
        method_names = sorted([i for i in dir(self) if i.startswith("_validate") and callable(getattr(self, i))])
        for method_name in method_names:
            method = getattr(self, method_name)
            method()

    def _get_parser(self):
        return {}

    def load(self, f):
        """
        Load data from a file.

        :param f: file-like object or path to file
        :type f: file or str
        """
        open_file = isinstance(f, six.string_types)
        if open_file:
            f = open(f, "r")
        parser = self.parse_file(f)
        self.deserialize(parser)
        if open_file:
            f.close()

    def loads(self, s):
        """
        Load data from a string.

        :param s: input data
        :type s: str
        """
        io = six.StringIO()
        io.write(s)
        io.seek(0)
        self.load(io)
        self.validate()

    def dump(self, f):
        """
        Dump data to a file.

        :param f: file-like object or path to file
        :type f: file or str
        """
        self.validate()
        open_file = isinstance(f, six.string_types)
        if open_file:
            f = open(f, "w")
        parser = self._get_parser()
        self.serialize(parser)
        self.build_file(parser, f)
        if open_file:
            f.close()

    def dumps(self):
        """
        Dump data to a string.

        :rtype: str
        """
        io = six.StringIO()
        self.dump(io)
        io.seek(0)
        return io.read()

    def parse_file(self, f):
        # parse file, return parser or dict with data
        f.seek(0)
        parser = json.load(f)
        return parser

    def build_file(self, parser, f):
        # build file from parser or dict with data
        json.dump(parser, f, indent=4, sort_keys=True)

    def deserialize(self, parser):
        # copy data from parser to instance
        raise NotImplementedError

    def serialize(self, parser):
        # copy data from instance to parser
        raise NotImplementedError


class Header(MetadataBase):

    def __init__(self, parent):
        self._section = "header"
        self.parent = parent
        self.version = "0.0"

    def _validate_version(self):
        self._assert_type("version", six.string_types)
        if re.match('^\d', self.version):
            self._assert_matches_re("version", [r"^\d+(\.\d+)*$"])

    @property
    def version_tuple(self):
        self.validate()
        return tuple(split_version(self.version))

    def set_current_version(self):
        self.version = ".".join([str(i) for i in VERSION])

    def serialize(self, parser):
        # write *current* version, because format gets converted on save
        self.set_current_version()
        self.validate()
        data = parser
        data[self._section] = {}
        data[self._section]["version"] = self.version

    def deserialize(self, parser):
        data = parser
        self.version = data[self._section]["version"]
        self.validate()


def split_version(version_str):
    result = version_str.split(".")
    for i in range(len(result)):
        result[i] = int(result[i])
    return result


def get_major_version(version, remove=1):
    version_split = version.split(".")
    if len(version_split) <= remove:
        return version
    return ".".join(version_split[:-remove])


def get_minor_version(version, remove=1):
    version_split = version.split(".")
    if len(version_split) <= remove:
        return None
    return ".".join(version_split[-remove:])


class SortedDict(dict):
    def __iter__(self):
        for key in self.keys():
            yield key

    def iterkeys(self):
        for key in self.keys():
            yield key

    def itervalues(self):
        for key in self.keys():
            yield self[key]

    def keys(self):
        return sorted(dict.keys(self), reverse=False)

    def iteritems(self):
        for key in self.keys():
            yield (key, self[key])

    def items(self):
        return self.iteritems()


class SortedConfigParser(ConfigParser):
    def __init__(self, *args, **kwargs):
        if sys.version_info[0] == 2:
            if sys.version_info[:2] >= (2, 6):
                # SafeConfigParser(dict_type=) supported in 2.6+
                kwargs["dict_type"] = SortedDict
            ConfigParser.__init__(self, *args, **kwargs)
        else:
            kwargs["dict_type"] = SortedDict
            super(ConfigParser, self).__init__(*args, **kwargs)
        self.seen = set()

    def optionxform(self, optionstr):
        # don't convert options to lower()
        return optionstr

    def option_lookup(self, section_option_list, default=None):
        for section, option in section_option_list:
            if self.has_option(section, option):
                return self.get(section, option)
        return default

    def read_file(self, *args, **kwargs):
        if sys.version_info[0] == 2:
            return self.readfp(*args, **kwargs)
        return super(SortedConfigParser, self).read_file(*args, **kwargs)
