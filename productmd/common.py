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


import sys
import re
import json
try:
    from configparser import ConfigParser
except ImportError:
    from ConfigParser import SafeConfigParser as ConfigParser

import six


VERSION = (1, 2)


__all__ = (
    "MetadataBase",
    "Header",
    "VERSION",

    "RELEASE_SHORT_RE",
    "RELEASE_VERSION_RE",
    "RELEASE_TYPES",

    "parse_nvra",
    "is_valid_release_short",
    "is_valid_release_version",
    "is_valid_release_type",
    "split_version",
    "get_major_version",
    "get_minor_version",
    "create_release_id",
    "parse_release_id",
)


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


#: Pattern to parse RPM N-E:V-R.A
RPM_NVRA_RE = re.compile(r"^(.*/)?(?P<name>.*)-((?P<epoch>\d+):)?(?P<version>.*)-(?P<release>.*)\.(?P<arch>.*)$")


def parse_nvra(nvra):
    """
    Parse RPM N-E:V-R.A string to a dict.

    :param nvra: N-E:V-R.A string, eventually a file name or a file path incl. '.rpm' suffix
    :type nvra: str
    :rtype: dict
    """
    if nvra.endswith(".rpm"):
        nvra = nvra[:-4]
    result = RPM_NVRA_RE.match(nvra).groupdict()
    result["epoch"] = result["epoch"] or 0
    result["epoch"] = int(result["epoch"])
    return result


#: Validation regex for release short name: [a-z] followed by [a-z0-9] separated with dashes.
RELEASE_SHORT_RE = re.compile("^[a-z]+([a-z0-9]*-?[a-z0-9]+)*$")


#: Validation regex for release version: any string or [0-9] separated with dots.
RELEASE_VERSION_RE = re.compile("^([^0-9].*|([0-9]+(\.?[0-9]+)*))$")


#: Supported release types.
RELEASE_TYPES = [
    "fast",
    "ga",
    "updates",
    "eus",
    "aus",
    "els",
]


def is_valid_release_short(short):
    """
    Determine if given release short name is valid.

    :param short: Release short name
    :type short: str
    :rtype: bool
    """
    match = RELEASE_SHORT_RE.match(short)
    return match is not None


def is_valid_release_version(version):
    """
    Determine if given release version is valid.

    :param version: Release version
    :type version: str
    :rtype: bool
    """
    match = RELEASE_VERSION_RE.match(version)
    return match is not None


def is_valid_release_type(release_type):
    """
    Determine if given release type is valid.

    :param release_type: Release type
    :type release_type: str
    :rtype: bool
    """
    return release_type in RELEASE_TYPES


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
        json.dump(parser, f, indent=4, sort_keys=True, separators = (",", ": "))

    def deserialize(self, parser):
        # copy data from parser to instance
        raise NotImplementedError

    def serialize(self, parser):
        # copy data from instance to parser
        raise NotImplementedError


class Header(MetadataBase):
    """
    This class represents the header used in serialized metadata files.

    It consists of a type and a version. The type is meant purely for consumers
    of the file to know what they are dealing with without having to check
    filename. The version is used by productmd when parsing the file.
    """

    def __init__(self, parent, metadata_type):
        self._section = "header"
        self.parent = parent
        self.version = "0.0"
        self.metadata_type = metadata_type

    def _validate_version(self):
        self._assert_type("version", six.string_types)
        self._assert_matches_re("version", [r"^\d+\.\d+$"])

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
        data[self._section]["type"] = self.metadata_type
        data[self._section]["version"] = self.version

    def deserialize(self, parser):
        data = parser
        self.version = data[self._section]["version"]
        if self.version_tuple >= (1, 1):
            metadata_type = data[self._section]["type"]
            if metadata_type != self.metadata_type:
                raise ValueError("Invalid metadata type '%s', expected '%s'" % (metadata_type, self.metadata_type))
        self.validate()


def split_version(version):
    """
    Split version to a list of integers
    that can be easily compared.

    :param version: Release version
    :type version: str
    :rtype: [int] or [string]
    """
    if re.match("^[^0-9].*", version):
        return [version]
    return [int(i) for i in version.split(".")]


def get_major_version(version, remove=1):
    """
    Return major version of a provided version string.

    :param version: Version string
    :type version: str
    :param remove: Number of version parts to remove; defaults to 1
    :type remove: int
    :rtype: str
    """
    version_split = version.split(".")
    if len(version_split) <= remove:
        return version
    return ".".join(version_split[:-remove])


def get_minor_version(version, remove=1):
    """
    Return minor version of a provided version string.

    :param version: Version string
    :type version: str
    :param remove: Number of version parts to remove; defaults to 1
    :type remove: int
    :rtype: str
    """
    version_split = version.split(".")
    if len(version_split) <= remove:
        return None
    return ".".join(version_split[-remove:])


def create_release_id(short, version, type, bp_short=None, bp_version=None, bp_type=None):
    """
    Create release_id from given parts.

    :param short: Release short name
    :type short: str
    :param version: Release version
    :type version: str
    :param version: Release type
    :type version: str
    :param bp_short: Base Product short name
    :type bp_short: str
    :param bp_version: Base Product version
    :type bp_version: str
    :param bp_version: Base Product type
    :rtype: str
    """
    if not is_valid_release_short(short):
        raise ValueError("Release short name is not valid: %s" % short)
    if not is_valid_release_version(version):
        raise ValueError("Release short version is not valid: %s" % version)
    if not is_valid_release_type(type):
        raise ValueError("Release type is not valid: %s" % type)

    if type == "ga":
        result = "%s-%s" % (short, version)
    else:
        result = "%s-%s-%s" % (short, version, type)

    if bp_short:
        result += "@%s" % create_release_id(bp_short, bp_version, bp_type)

    return result


def parse_release_id(release_id):
    """
    Parse release_id to parts:
    {short, version, type}
    or
    {short, version, type, bp_short, bp_version, bp_type}

    :param release_id: Release ID string
    :type release_id: str
    :rtype: dict
    """
    if "@" in release_id:
        release, base_product = release_id.split("@")
    else:
        release = release_id
        base_product = None

    result = _parse_release_id_part(release)
    if base_product is not None:
        result.update(_parse_release_id_part(base_product, prefix="bp_"))
    return result


def _parse_release_id_part(release_id, prefix=""):
    if release_id.count("-") == 1:
        # TODO: what if short contains '-'?
        short, version = release_id.split("-")
        release_type = "ga"
    else:
        short, version, release_type = release_id.rsplit("-", 2)
    result = {
        "short": short,
        "version": version,
        "type": release_type,
    }
    result = dict([("%s%s" % (prefix, key), value) for key, value in result.items()])
    return result


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
