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
This module provides classes for manipulating composeinfo.json files.
composeinfo.json files provide details about composes which includes
product information, variants, architectures and paths.
"""


import re

import productmd.common
from productmd.common import Header, RELEASE_VERSION_RE

import six


__all__ = (
    "ComposeInfo",
    "COMPOSE_TYPES",
    "LABEL_NAMES",
    "VARIANT_TYPES",
)


if six.PY3:
    def cmp(a, b):
        return (a > b) - (a < b)


# order matters - used in __cmp__
# least important come first
#: supported compose types
COMPOSE_TYPES = [
    "test",             # for test purposes only
    "ci",               # continuous integration, frequently from an automatically generated package set
    "nightly",          # nightly composes from production package set
    "production",       # production composes
]


#: supported milestone label names
LABEL_NAMES = [
    "DevelPhaseExit",
    "InternalAlpha",
    "Alpha",
    "InternalSnapshot",
    "Beta",
    "Snapshot",
    "RC",
    "Update",
]


LABEL_RE_LIST = []
for label_name in LABEL_NAMES:
    # create $label_name-$major_ver.$minor_ver patterns
    LABEL_RE_LIST.append(re.compile(r"^%s-\d+\.\d+$" % label_name))


#: supported variant types
VARIANT_TYPES = [
    "variant",
    "optional",
    "addon",
    "layered-product",
]


class ComposeInfo(productmd.common.MetadataBase):
    """
    This class only encapsulates other classes with actual data.
    """

    def __init__(self):
        super(ComposeInfo, self).__init__()

        self.header = Header(self, "productmd.composeinfo")     #: (:class:`.Header`) -- Metadata header
        self.compose = Compose(self)            #: (:class:`.Compose`) -- Compose details
        self.release = Release(self)            #: (:class:`.Release`) -- Release details
        self.base_product = BaseProduct(self)   #: (:class:`.BaseProduct`) -- Base product details (optional)
        self.variants = Variants(self)          #: (:class:`.Variants`) -- release variants
        self.validate()
        self.header.set_current_version()

    def __str__(self):
        result = self.release_id
        if self.compose.label:
            result += " (%s)" % self.compose.label
        return result

    def __cmp__(self, other):
        result = cmp(self.release, other.release)
        if result != 0:
            return result

        result = cmp(self.base_product, other.base_product)
        if result != 0:
            return result

        result = cmp(self.compose, other.compose)
        if result != 0:
            return result

        return 0

    def get_release_id(self, major_version=False):
        if major_version:
            result = "%s-%s" % (self.release.short, self.release.major_version)
        else:
            result = "%s-%s" % (self.release.short, self.release.version)
        if self.release.is_layered:
            result += "-%s-%s" % (self.base_product.short, self.base_product.version)
        return result

    @property
    def release_id(self):
        return self.get_release_id()

    def create_compose_id(self):
        result = "%s-%s%s" % (self.release.short, self.release.version,
                              self.release.type_suffix)
        if self.release.is_layered:
            result += "-%s-%s%s" % (self.base_product.short,
                                    self.base_product.version,
                                    self.base_product.type_suffix)

        rhel5 = (self.release.short == "RHEL" and self.release.major_version == "5")
        rhel5 &= (self.base_product.short == "RHEL" and self.base_product.major_version == "5")
        if rhel5:
            # HACK: there are 2 RHEL 5 composes -> need to add Server or Client variant to compose ID
            if self.variants.variants:
                variant = sorted(self.variants.variants)[0]
                if variant in ("Client", "Server"):
                    result += "-%s" % variant
        result += "-%s%s.%s" % (self.compose.date, self.compose.type_suffix, self.compose.respin)
        return result

    def serialize(self, parser):
        data = parser
        self.header.serialize(data)
        data["payload"] = {}
        self.compose.serialize(data["payload"])
        self.release.serialize(data["payload"])
        if self.release.is_layered:
            self.base_product.serialize(data["payload"])
        self.variants.serialize(data["payload"])
        return data

    def deserialize(self, data):
        self.header.deserialize(data)
        self.compose.deserialize(data["payload"])
        self.release.deserialize(data["payload"])
        if self.release.is_layered:
            self.base_product.deserialize(data["payload"])
        self.variants.deserialize(data["payload"])
        self.header.set_current_version()

    def __getitem__(self, name):
        return self.variants[name]

    def get_variants(self, *args, **kwargs):
        return self.variants.get_variants(*args, **kwargs)


def verify_label(label):
    if label is None:
        return
    found = False
    for pattern in LABEL_RE_LIST:
        if pattern.match(label):
            found = True
            break
    if not found:
        raise ValueError("Label in unknown format: %s" % label)
    return label


def get_date_type_respin(compose_id):
    pattern = re.compile(r".*(?P<date>\d{8})(?P<type>\.nightly|\.n|\.test|\.t|\.ci)?(\.(?P<respin>\d+))?.*")
    match = pattern.match(compose_id)
    if not match:
        return None, None, None
    result = match.groupdict()
    if result["respin"] is None:
        result["respin"] = 0
    if not result["type"]:
        result["type"] = "production"
    elif result["type"] in (".nightly", ".n"):
        result["type"] = "nightly"
    elif result["type"] in (".test", ".t"):
        result["type"] = "test"
    elif result["type"] == ".ci":
        result["type"] = "ci"
    else:
        raise ValueError("Unknown compose type: %s" % result["type"])
    return (result["date"], result["type"], int(result["respin"]))


def parse_compose_id(compose_id):
    """Parse a compose ID back into its component values. Returns a
    dict containing values for 'short', 'version', 'version_type',
    'bp_short', 'bp_version', 'bp_type', 'variant', 'date',
    'compose_type' and 'respin'. If the ID is not for a layered
    compose, the 'bp_*' values will be ''. The 'variant value will
    only be populated (as 'Client' or 'Server') for RHEL 5 composes
    (see `ComposeInfo.create_compose_id`). 'date', 'compose_type' and
    'respin' are the output of `common.get_date_type_respin`. May
    raise ValueError for pathologically unparseable compose IDs. Can
    be fooled by very weird shortnames: for instance, if you were to
    use 'f-26-r' as a shortname, resulting in a compose ID like
    'f-26-r-23-20170225.n.0', then this parser will read that as a
    layered product compose ID, where bp_short is 'r', bp_version is
    '23', short is 'f' and version is '26'.
    """
    # init values
    short = ''
    version = ''
    version_type = ''
    bp_short = ''
    bp_version = ''
    bp_type = ''
    variant = ''

    # find date, type, respin
    (date, compose_type, respin) = get_date_type_respin(compose_id)
    # now split on the date, we only care about what comes before
    part = compose_id.rsplit(date, 1)[0][:-1]

    # Handle "HACK: there are 2 RHEL 5 composes"
    if part.endswith("-Client"):
        variant = "Client"
        part = part[:-len('-Client')]
    elif part.endswith("-Server"):
        variant = "Server"
        part = part[:-len('-Server')]

    # Next part back must be either a version type suffix or a version
    # we don't know yet if this is the main version or the base
    # version for a layered product
    (part, somever) = part.rsplit('-', 1)
    # See if it's a type_suffix
    if somever.lower() in productmd.common.RELEASE_TYPES:
        sometype = somever
        (part, somever) = part.rsplit('-', 1)
    else:
        sometype = ''

    # what remains is either:
    # short
    # or:
    # short-version(-version_type)-bp_short
    # But this is where things get fun, because sadly, both short
    # and bp_short could have - in them and version could have a type
    # suffix. So, life is fun. Let's see if we can spot what looks
    # like a '-version(-type)' component. Note that particularly evil
    # shortnames can screw us up here: see the comment where we check
    # the length of `goodmatches`.
    elems = part.split('-')
    # Only do this magic if we have at least 3 elems, because if we
    # have 1 or 2, we know it's just the shortname.
    if len(elems) > 2:
        # use this to track all of the RELEASE_VERSION_RE matches we
        # find
        matches = []
        for (idx, cand) in enumerate(elems):
            # can't be the first or the last
            if idx == 0 or idx == len(elems) - 1:
                continue
            # now see if the cand looks like a version
            match = RELEASE_VERSION_RE.match(cand)
            if match:
                matchver = match.group(1)
                # check if the next element looks like a version type
                nextel = elems[idx+1]
                if nextel.lower() in productmd.common.RELEASE_TYPES:
                    # if we got *two* matches that look like
                    # -version-version_type- , we're pretty screwed
                    matchtype = nextel
                else:
                    matchtype = ''
                matches.append((matchver, matchtype, idx))

        # find all matches that produce two valid short names
        goodmatches = []
        for match in matches:
            (_version, _version_type, idx) = match
            _short = '-'.join(elems[:idx])
            if _version_type:
                _bp_short = '-'.join(elems[idx+2:])
            else:
                _bp_short = '-'.join(elems[idx+1:])
            if all(productmd.common.is_valid_release_short(shrt) for shrt in (_short, _bp_short)):
                goodmatches.append(match)

        if len(goodmatches) > 1:
            # we're boned. you have to work quite hard to get here,
            # though. this will do it: 'F-26-F-26-RHEL-6-20170225.n.0'
            # where the shortname and base shortname could be either
            # 'F' and 'F-26-RHEL' or 'F-26-F' and 'RHEL'.
            raise ValueError("Cannot parse compose ID %s as it contains more than one possible "
                             "-version(-version_type)- string" % compose_id)

        if goodmatches:
            (version, version_type, idx) = goodmatches[0]
            bp_version = somever
            bp_type = sometype
            short = '-'.join(elems[:idx])
            if version_type:
                bp_short = '-'.join(elems[idx+2:])
            else:
                bp_short = '-'.join(elems[idx+1:])

    # if we didn't establish a version above, we must not be layered,
    # and what remains is just short, and somever is version
    if not short:
        short = part
        version = somever
        version_type = sometype

    if not version_type:
        version_type = 'ga'
    if bp_version and not bp_type:
        bp_type = 'ga'

    return {
        'short': short,
        'version': version,
        'version_type': version_type,
        'bp_short': bp_short,
        'bp_version': bp_version,
        'bp_type': bp_type,
        'variant': variant,
        'date': date,
        'compose_type': compose_type,
        'respin': respin
    }


def cmp_label(label1, label2):
    name1, ver1 = label1.rsplit("-", 1)
    name2, ver2 = label2.rsplit("-", 1)

    index1 = LABEL_NAMES.index(name1)
    index2 = LABEL_NAMES.index(name2)
    if index1 != index2:
        return cmp(index1, index2)

    split_ver1 = productmd.common.split_version(ver1)
    split_ver2 = productmd.common.split_version(ver2)
    return cmp(split_ver1, split_ver2)


class Compose(productmd.common.MetadataBase):

    def __init__(self, metadata):
        super(Compose, self).__init__()
        self._section = "compose"
        self._metadata = metadata
        self.id = None
        self.type = None
        self.date = None
        self.respin = None
        self.label = None
        self.final = False

    def __repr__(self):
        return u'<%s:%s>' % (self.__class__.__name__, self.id)

    def __cmp__(self, other):
        result = cmp(self.date, other.date)
        if result != 0:
            return result

        if self.type != other.type:
            return cmp(COMPOSE_TYPES.index(self.type), COMPOSE_TYPES.index(other.type))

        result = cmp(self.respin, other.respin)
        if result != 0:
            return result

        return 0

    def _validate_id(self):
        self._assert_type("id", list(six.string_types))
        self._assert_not_blank("id")
        self._assert_matches_re("id", [r".*\d{8}(\.nightly|\.n|\.ci|\.test|\.t)?(\.\d+)?"])

    def _validate_date(self):
        self._assert_type("date", list(six.string_types))
        self._assert_matches_re("date", [r"^\d{8}$"])

    def _validate_type(self):
        self._assert_value("type", COMPOSE_TYPES)

    def _validate_respin(self):
        self._assert_type("respin", list(six.integer_types))

    def _validate_label(self):
        self._assert_type("label", [type(None)] + list(six.string_types))
        verify_label(self.label)

    def _validate_final(self):
        if self.label:
            self._assert_type("final", [bool])

    @property
    def is_ga(self):
        if not self.label:
            return False
        label_name = self.label.split("-")[0]
        if label_name == "RC" and self.final:
            return True
        return False

    @property
    def full_label(self):
        if not self.label:
            return None
        # TODO: layered products
        return "%s-%s %s" % (self._metadata.release.short, self._metadata.release.version, self.label)

    @property
    def label_major_version(self):
        """Return major version for a label.

        Examples: Beta-1.2 -> Beta-1, GA -> GA
        """
        if not self.label:
            return None
        return self.label.rsplit(".", 1)[0]

    @property
    def type_suffix(self):
        if self.type == "production":
            return ""
        if self.type == "ci":
            return ".ci"
        if self.type == "nightly":
            return ".n"
        if self.type == "test":
            return ".t"
        raise ValueError("Invalid compose type: %s" % self.type)

    def serialize(self, data):
        self.validate()
        data[self._section] = {}
        data[self._section]["id"] = self.id
        data[self._section]["type"] = self.type
        data[self._section]["date"] = self.date
        data[self._section]["respin"] = self.respin
        if self.label:
            data[self._section]["label"] = self.label
            data[self._section]["final"] = self.final

    def deserialize(self, data):
        if self._metadata.header.version_tuple < (0, 3):
            self.deserialize_0_3(data)
        else:
            self.deserialize_1_0(data)
        self.validate()

    def deserialize_0_3(self, data):
        self.id = data[self._section]["id"]
        self.label = data[self._section].get("label", None) or None
        self.type = data[self._section]["type"]
        self.date, self.type, self.respin = get_date_type_respin(self.id)
        self.final = bool(data[self._section].get("final", False))

    def deserialize_1_0(self, data):
        self.id = data[self._section]["id"]
        self.label = data[self._section].get("label", None) or None
        self.type = data[self._section]["type"]
        self.date = data[self._section]["date"]
        self.respin = data[self._section]["respin"]
        self.final = bool(data[self._section].get("final", False))


class BaseProduct(productmd.common.MetadataBase):
    """
    This class represents a base product a release is based on.
    For example: Spacewalk 2.2 release requires Fedora 20 base product.
    Information from this class is used only if release.is_layered is set.
    """

    def __init__(self, metadata):
        super(BaseProduct, self).__init__()
        self._section = "base_product"
        self._metadata = metadata
        self.name = None        #: (*str*) -- Product name, for example: "Fedora", "Red Hat Enterprise Linux"
        self.version = None     #: (*str*) -- Product version (typically major version), for example: "20", "7"
        self.short = None       #: (*str*) -- Product short name, for example: "f", "rhel"
        self.type = None        #: (*str*) -- Product type, for example: "ga", "eus"

    def __repr__(self):
        return u'<%s:%s:%s>' % (self.__class__.__name__, self.name, self.version)

    def __cmp__(self, other):
        if self.name != other.name:
            raise ValueError("Comparing incompatible products: %s vs %s" % (self.name, other.name))
        if self.short != other.short:
            raise ValueError("Comparing incompatible products: %s vs %s" % (self.short, other.short))
        if self.version != other.version:
            return cmp(productmd.common.split_version(self.version), productmd.common.split_version(other.version))
        return 0

    def __str__(self):
        return "%s-%s" % (self.short, self.version)

    def _validate_name(self):
        self._assert_type("name", list(six.string_types))

    def _validate_version(self):
        """If the version starts with a digit, it must be a sematic-versioning
        style string.
        """
        self._assert_type("version", list(six.string_types))
        self._assert_matches_re("version", [RELEASE_VERSION_RE])

    def _validate_short(self):
        self._assert_type("short", list(six.string_types))

    def _validate_type(self):
        self._assert_type("type", list(six.string_types))
        self._assert_value("type", productmd.common.RELEASE_TYPES)

    @property
    def major_version(self):
        if self.version is None:
            return None
        return productmd.common.get_major_version(self.version)

    @property
    def minor_version(self):
        if self.version is None:
            return None
        return productmd.common.get_minor_version(self.version)

    @property
    def type_suffix(self):
        """This is used in compose ID."""
        if not self.type or self.type.lower() == 'ga':
            return ''
        return '-%s' % self.type.lower()

    def serialize(self, data):
        self.validate()
        data[self._section] = {}
        data[self._section]["name"] = self.name
        data[self._section]["version"] = self.version
        data[self._section]["short"] = self.short
        data[self._section]["type"] = self.type

    def deserialize(self, data):
        self.name = data[self._section]["name"]
        self.version = data[self._section]["version"]
        self.short = data[self._section]["short"]
        self.type = data[self._section].get("type", "ga")
        self.validate()


class Release(BaseProduct):
    """
    This class represents a product release.
    """

    def __init__(self, metadata):
        super(Release, self).__init__(metadata)
        self._section = "release"

        self.name = None                #: (*str*) -- Release name, for example: "Fedora", "Red Hat Enterprise Linux"
        self.version = None             #: (*str*) -- Release version (incl. minor version), for example: "20", "7.0"
        self.short = None               #: (*str*) -- Release short name, for example: "f", "rhel"
        self.type = None                #: (*str*) -- Release type, for example: "ga", "updates"
        self.is_layered = False         #: (*bool=False*) -- Determines if release is a layered product
        self.internal = False           #: (*bool=False*) -- Determine if release is meant for public consumption

    def __cmp__(self, other):
        if self.is_layered != other.is_layered:
            raise ValueError("Comparing layered with non-layered product: %s vs %s" % (self, other))
        return BaseProduct.__cmp__(self, other)

    def _validate_type(self):
        self._assert_type("type", list(six.string_types))
        self._assert_value("type", productmd.common.RELEASE_TYPES)

    def _validate_is_layered(self):
        self._assert_type("is_layered", [bool])

    def _validate_internal(self):
        self._assert_type("internal", [bool])

    def serialize(self, data):
        self.validate()
        data[self._section] = {}
        data[self._section]["name"] = self.name
        data[self._section]["version"] = self.version
        data[self._section]["short"] = self.short
        data[self._section]["type"] = self.type
        if self.is_layered:
            data[self._section]["is_layered"] = bool(self.is_layered)
        data[self._section]["internal"] = bool(self.internal)

    def deserialize(self, data):
        if self._metadata.header.version_tuple <= (0, 3):
            self.deserialize_0_3(data)
        else:
            self.deserialize_1_0(data)
        self.validate()

    def deserialize_0_3(self, data):
        self.name = data["product"]["name"]
        self.version = data["product"]["version"]
        self.short = data["product"]["short"]
        self.type = data["product"].get("type", "ga").lower()
        self.is_layered = bool(data["product"].get("is_layered", False))

    def deserialize_1_0(self, data):
        self.name = data[self._section]["name"]
        self.version = data[self._section]["version"]
        self.short = data[self._section]["short"]
        self.type = data[self._section].get("type", "ga").lower()
        self.is_layered = bool(data[self._section].get("is_layered", False))
        self.internal = bool(data[self._section].get("internal", False))


class VariantBase(productmd.common.MetadataBase):
    def __init__(self, metadata):
        super(VariantBase, self).__init__()
        self._metadata = metadata
        self.parent = None
        self.variants = {}

    def __repr__(self):
        return u'<%s:%s>' % (self.__class__.__name__, self._metadata.compose.id)

    def __getitem__(self, name):
        # There can be exceptions, like $variant-optional on top-level,
        # because optional lives in a separate tree
        if name not in self.variants and "-" in name:
            # look for the UID first
            for i in self.variants:
                var = self.variants[i]
                if var.uid == name:
                    return var
            # if UID is not found, split and look for variant matching the parts
            head, tail = name.split("-", 1)
            return self.variants[head][tail]
        return self.variants[name]

    def __delitem__(self, name):
        if name not in self.variants and "-" in name:
            head, tail = name.split("-", 1)
            del self.variants[head][tail]
        else:
            del self.variants[name]

    def __iter__(self):
        for i in sorted(self.variants.keys()):
            yield i

    def __len__(self):
        return len(self.variants)

    def _validate_variants(self):
        for variant_id in self:
            variant = self[variant_id]
            if variant.id != variant_id:
                raise ValueError("Variant ID doesn't match: '%s' vs '%s'" % (variant.id, variant_id))

    def add(self, variant, variant_id=None):
        if hasattr(self, "uid"):
            # detect Variant; we don't want to set parent for VariantBase or Variants
            variant.parent = self

        variant.validate()
        variant_id = variant_id or variant.id
        if hasattr(self, "parent"):
            parents = self._get_all_parents()
            if variant in parents:
                parent_uids = sorted([i.uid for i in parents])
                raise ValueError("Dependency cycle detected; variant %s; parents: %s" % (variant.uid, parent_uids))
        new_variant = self.variants.setdefault(variant_id, variant)
        if new_variant != variant:
            raise ValueError("Variant ID already exists: %s" % variant.id)

    def _get_all_parents(self):
        result = [self]
        if self.parent:
            result.extend(self.parent._get_all_parents())
        return result

    def get_variants(self, arch=None, types=None, recursive=False):
        """
        Return all variants of given arch and types.

        Supported variant types:
            self     - include the top-level ("self") variant as well
            addon
            variant
            optional
        """
        types = types or []
        result = []

        if "self" in types:
            result.append(self)

        for variant in six.itervalues(self.variants):
            if types and variant.type not in types:
                continue
            if arch and arch not in variant.arches.union(["src"]):
                continue
            result.append(variant)
            if recursive:
                result.extend(variant.get_variants(types=[i for i in types if i != "self"], recursive=True))

        result.sort(key=lambda x: x.uid)
        return result


class Variants(VariantBase):
    """
    This class is a container for compose variants.
    """
    def __init__(self, metadata):
        super(Variants, self).__init__(metadata)
        self._section = "variants"

    def serialize(self, data):
        self.validate()

        data[self._section] = {}

        # variant UIDs should be identical to IDs at the top level
        variant_ids = sorted(self.variants.keys())

        for variant_id in variant_ids:
            variant = self.variants[variant_id]
            variant.serialize(data[self._section])

    def deserialize(self, data):
        # variant UIDs should be identical to IDs at the top level
        all_variants = data[self._section].keys()

        variant_ids = []
        for variant_uid, var in data[self._section].items():
            if "-" in variant_uid:
                head, tail = variant_uid.rsplit("-", 1)
                if head in all_variants:
                    # has parent
                    continue
                variant_ids.append(variant_uid)
            else:
                variant_ids.append(variant_uid)

        variant_ids.sort()
        for variant_id in variant_ids:
            variant = Variant(self._metadata)
            variant.deserialize(data[self._section], variant_id)
            self.add(variant)


class VariantPaths(productmd.common.MetadataBase):
    """
    This class stores relative paths for a variant in a compose.
    Paths are represented as dictionaries mapping arches to actual paths.
    List of supported paths follows.

    **Binary**

        * **os_tree** -- installable tree with binary RPMs, kickstart trees, readme etc.
        * **packages** -- directory with binary RPMs
        * **repository** -- YUM repository with binary RPMs
        * **isos** -- Binary ISOs
        * **jigdos** -- Jigdo files for binary ISOs

    **Source**

        * **source_tree** -- tree with source RPMs
        * **source_packages** -- directory with source RPMs
        * **source_repository** -- YUM repository with source RPMs
        * **source_isos** -- Source ISOs
        * **source_jigdos** -- Jigdo files for source ISOs

    **Debug**

        * **debug_tree** -- tree with debug RPMs
        * **debug_packages** -- directory with debug RPMs
        * **debug_repository** -- YUM repository with debug RPMs

    Example::

        self.os_tree = {
            "i386": "Server/i386/os",
            "x86_64": "Server/x86_64/os",
        }
        self.packages = {
            "i386": "Server/i386/os/Packages",
            "x86_64": "Server/x86_64/os/Packages",
        }
    """

    def __init__(self, variant):
        self._variant = variant
        self.parent = None

        # paths: product certificate
        self.identity = {}

        self._fields = [
            # binary
            "os_tree",
            "packages",
            "repository",
            "isos",
            "jigdos",

            # source
            "source_tree",
            "source_packages",
            "source_repository",
            "source_isos",
            "source_jigdos",

            # debug
            "debug_tree",
            "debug_packages",
            "debug_repository",
            # debug isos and jigdos are not supported
        ]

        for name in self._fields:
            setattr(self, name, {})

    def __repr__(self):
        return u'<%s:variant=%s>' % (self.__class__.__name__, self._variant.uid)

    def deserialize(self, data):
        paths = data
        for arch in sorted(self._variant.arches):
            for name in self._fields:
                value = paths.get(name, {}).get(arch, None)
                if value:
                    field = getattr(self, name)
                    field[arch] = value
        self.validate()

    def serialize(self, data):
        self.validate()
        paths = data
        for arch in sorted(self._variant.arches):
            for name in self._fields:
                field = getattr(self, name)
                value = field.get(arch, None)
                if value:
                    paths.setdefault(name, {})[arch] = value


class Variant(VariantBase):
    def __init__(self, metadata):
        VariantBase.__init__(self, metadata)

        # variant details
        self.id = None          #: (*str*) -- variant ID, for example: "Client", "Server", "optional"
        self.uid = None         #: (*str*) -- variant unique ID: $PARENT_UID-$ID, for example: "Server-optional"
        self.name = None        #: (*str*) -- variant name (pretty text), for example: "Enterprise Server"
        self.type = None        #: (*str*) -- variant type, see VARIANT_TYPES for supported values
        self.arches = set()     #: (*set(<str>)*) -- set of arches for a variant
        self.variants = {}      #: (*dict*) -- child variants
        self.parent = None      #: (:class:`.Variant` or *None*) -- parent variant

        self.paths = VariantPaths(self)         #: (:class:`VariantPaths`) -- path mappings for a variant
        # for self.type == "layered-product"
        self.release = Release(self._metadata)  #: (:class:`Release`) --
        self.release.is_layered = True

    def __str__(self):
        return self.uid

    def __repr__(self):
        return u'<%s:%s>' % (self.__class__.__name__, self.uid)

    def _validate_id(self):
        self._assert_type("id", list(six.string_types))
        self._assert_matches_re("id", [r"^[a-zA-Z0-9]+$"])

    def _validate_uid(self):
        if self.parent is None:
            uid = self.id
            self_uid = self.uid.replace("-", "")
        else:
            uid = "%s-%s" % (self.parent.uid, self.id)
            self_uid = self.uid

        if self_uid != uid:
            raise ValueError("UID '%s' doesn't align with parent UID '%s'" % (self.uid, uid))

    def _validate_name(self):
        self._assert_type("name", list(six.string_types))
        self._assert_not_blank("name")

    def _validate_type(self):
        self._assert_value("type", VARIANT_TYPES)

    def _validate_arches(self):
        self._assert_not_blank("arches")

    def _validate_parent_arch(self):
        if not self.parent:
            return
        for arch in self.arches:
            if arch not in self.parent.arches:
                raise ValueError("Variant '%s': arch '%s' not found in parent arches %s" % (self.uid, arch, sorted(self.parent.arches)))

    @property
    def compose_id(self):
        if self.type == "layered-product":
            result = "%s-%s" % (self.release.short, self.release.version)
            result += "-%s-%s" % (self._metadata.release.short, self._metadata.release.major_version)
            result += "-%s%s.%s" % (self._metadata.compose.date, self._metadata.compose.type_suffix, self._metadata.compose.respin)
            return result
        return self._metadata.compose.id

    def deserialize(self, data, variant_uid):
        full_data = data
        data = data[variant_uid]

        # variant details
        self.id = data["id"]
        self.uid = data["uid"]
        self.name = data["name"]
        self.type = data["type"]
        self.arches = set(data["arches"])

        if self.type == "layered-product":
            self.release.deserialize(data)

        paths = data["paths"]
        self.paths.deserialize(paths)

        if "variants" in data:
            variant_ids = sorted(data["variants"])
            variant_uids = ["%s-%s" % (self.uid, i) for i in variant_ids]
        else:
            # legacy metadata with no "variants" parent-child references
            variant_uids = full_data.keys()
            variant_uids = [i for i in variant_uids if i.startswith("%s-" % variant_uid)]

        for variant_uid in variant_uids:
            variant = Variant(self._metadata)
            variant.parent = self
            variant.deserialize(full_data, variant_uid)
            self.add(variant)

        self.validate()

    def serialize(self, data):
        dump = {}

        # variant details
        dump["id"] = self.id
        dump["uid"] = self.uid
        dump["name"] = self.name
        dump["type"] = self.type
        dump["arches"] = sorted(self.arches)

        if self.type == "layered-product":
            self.release.is_layered = True
            self.release.serialize(dump)

        paths = dump.setdefault("paths", {})
        self.paths.serialize(paths)

        # variants
        variant_ids = set()
        for variant in self.variants.values():
            variant.serialize(data)
            variant_ids.add(variant.id)
        if variant_ids:
            dump["variants"] = sorted(variant_ids)

        new_dump = data.setdefault(self.uid, dump)
        if new_dump != dump:
            raise ValueError("Variant UID already exist: %s" % self.uid)

        self.validate()

    def add(self, variant):
        VariantBase.add(self, variant)
