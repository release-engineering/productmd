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


import os
import sys
import re
import json
import codecs
import contextlib
import ssl
import warnings

import six
from six.moves.configparser import ConfigParser


VERSION = (1, 2)


__all__ = (
    "MetadataBase",
    "Header",
    "VERSION",

    "RELEASE_SHORT_RE",
    "RELEASE_VERSION_RE",
    "RELEASE_TYPE_RE",
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

    :param nvra: N-E:V-R.A string. This can be a file name or a file path including the '.rpm' suffix.
    :type nvra: str
    :rtype: dict, with "name", "epoch", "version", "release", and "arch" elements.
    """
    if nvra.endswith(".rpm"):
        nvra = nvra[:-4]
    result = RPM_NVRA_RE.match(nvra).groupdict()
    result["epoch"] = result["epoch"] or 0
    result["epoch"] = int(result["epoch"])
    return result


#: Validation regex for release short name: [a-z] followed by [a-z0-9] separated with dashes.
RELEASE_SHORT_RE = re.compile(r"^[a-z]+([a-z0-9]*-?[a-z0-9]+)*$")


#: Validation regex for release version: any string or [0-9] separated with dots.
RELEASE_VERSION_RE = re.compile(r"^([^0-9].*|([0-9]+(\.?[0-9]+)*))$")


#: Validation regex for release type: [a-z] followed by [a-z0-9] separated with dashes.
RELEASE_TYPE_RE = re.compile(r"^[a-z]+([a-z0-9]*-?[a-z0-9]+)*$")


#: Known release types. New values need to be added here if they contain a
# dash, otherwise parsing release IDs will not be reliable.
RELEASE_TYPES = [
    "fast",
    "ga",
    "updates",
    "updates-testing",
    "eus",
    "aus",
    "els",
    "tus",
    "e4s",
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
    match = RELEASE_TYPE_RE.match(release_type)
    return match is not None


def _urlopen(path):
    kwargs = {}
    if hasattr(ssl, '_create_unverified_context'):
        # We only want to use the `context` keyword argument if it has a value.
        # Older Python versions (<2.7.9) do not support it. In those cases the
        # ssl module will not have the method to create the context.
        kwargs['context'] = ssl._create_unverified_context()
    return six.moves.urllib.request.urlopen(path, **kwargs)


@contextlib.contextmanager
def open_file_obj(f, mode="r"):
    """
    A context manager that provides access to a file.

    :param f: the file to be opened
    :type f: a file-like object or path to file
    :param mode: how to open the file
    :type mode: string
    """
    if isinstance(f, six.string_types):
        if f.startswith(("http://", "https://", "ftp://")):
            file_obj = _urlopen(f)
            yield file_obj
            file_obj.close()
        else:
            with open(f, mode) as file_obj:
                yield file_obj
    else:
        yield f


def _file_exists(path):
    if path.startswith(("http://", "https://", "ftp://")):
        try:
            file_obj = _urlopen(path)
            file_obj.close()
        except six.moves.urllib.error.HTTPError:
            return False
        return True
    return os.path.exists(path)


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
        """
        The list of patterns can contain either strings or compiled regular
        expressions.
        """
        value = getattr(self, field)
        for pattern in expected_patterns:
            try:
                if pattern.match(value):
                    return
            except AttributeError:
                # It's not a compiled regex, treat it as string.
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
        with open_file_obj(f) as f:
            parser = self.parse_file(f)
            self.deserialize(parser)

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
        with open_file_obj(f, "w") as f:
            parser = self._get_parser()
            self.serialize(parser)
            self.build_file(parser, f)

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
        if hasattr(f, "seekable"):
            if f.seekable():
                f.seek(0)
        elif hasattr(f, "seek"):
            f.seek(0)
        if six.PY3 and isinstance(f, six.moves.http_client.HTTPResponse):
            # HTTPResponse needs special handling in py3
            reader = codecs.getreader("utf-8")
            parser = json.load(reader(f))
        else:
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


def get_major_version(version, remove=None):
    """Return major version of a provided version string. Major version is the
    first component of the dot-separated version string. For non-version-like
    strings this function returns the argument unchanged.

    The ``remove`` parameter is deprecated since version 1.18 and will be
    removed in the future.

    :param version: Version string
    :type version: str
    :rtype: str
    """
    if remove:
        warnings.warn("remove argument is deprecated", DeprecationWarning)
    version_split = version.split(".")
    return version_split[0]


def get_minor_version(version, remove=None):
    """Return minor version of a provided version string. Minor version is the
    second component in the dot-separated version string. For non-version-like
    strings this function returns ``None``.

    The ``remove`` parameter is deprecated since version 1.18 and will be
    removed in the future.

    :param version: Version string
    :type version: str
    :rtype: str
    """
    if remove:
        warnings.warn("remove argument is deprecated", DeprecationWarning)
    version_split = version.split(".")
    try:
        # Assume MAJOR.MINOR.REST...
        return version_split[1]
    except IndexError:
        return None


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
    :param bp_type: Base Product type
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
        release_type = None
        for type_ in RELEASE_TYPES:
            # Try to find a known release type.
            if release_id.endswith(type_):
                release_type = type_
                break

        if release_type:
            # Found, remove it from the parsed string (because there could be a
            # dash causing problems).
            release_id = release_id[:-len(release_type)]

        short, version, release_type_extracted = release_id.rsplit("-", 2)

        # If known release type is found, use it; otherwise fall back to the
        # one we parsed out.
        release_type = release_type or release_type_extracted
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
            super(SortedConfigParser, self).__init__(*args, **kwargs)
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
