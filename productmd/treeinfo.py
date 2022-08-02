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
This module provides classes for manipulating .treeinfo files.
Treeinfo files provide details about installable trees in Fedora composes and media.
"""


import os
import hashlib
import re

import six

import productmd.common
import productmd.composeinfo


__all__ = (
    "TreeInfo",
    "Variant",
    "VARIANT_TYPES",
)


#: supported variant types
VARIANT_TYPES = [
    "variant",
    "optional",
    "addon",
]


def compute_checksum(path, checksum_type):
    checksum = hashlib.new(checksum_type)
    with open(path, "rb") as fo:
        while True:
            chunk = fo.read(1024**2)
            if not chunk:
                break
            checksum.update(chunk)
    return checksum.hexdigest().lower()


class TreeInfo(productmd.common.MetadataBase):
    def __init__(self):
        super(productmd.common.MetadataBase, self)
        self.header = Header(self, "productmd.treeinfo")        #: (:class:`productmd.common.Header`) -- Metadata header
        self.release = Release(self)            #: (:class:`.Release`) -- Release details
        self.base_product = BaseProduct(self)   #: (:class:`.BaseProduct`) -- Base product details (optional)
        self.tree = Tree(self)                  #: (:class:`.Tree`) -- Tree details
        self.variants = Variants(self)          #: (:class:`.Variants`) -- Release variants
        self.checksums = Checksums(self)        #: (:class:`.Checksums`) -- Checksums of images included in a tree
        self.images = Images(self)              #: (:class:`.Images`) -- Paths to images included in a tree
        self.stage2 = Stage2(self)              #: (:class:`.Stage2`) -- Stage 2 image path (for Anaconda installer)
        self.media = Media(self)                #: (:class:`.Media`) -- Media set information (optional)

    def __str__(self):
        result = "%s-%s" % (self.release.short, self.release.version)
        if self.release.is_layered:
            result += "-%s-%s" % (self.base_product.short, self.base_product.version)
        variant = sorted(self.variants)[0]
        result += " %s.%s" % (variant, self.tree.arch)
        return result

    def __getitem__(self, name):
        return self.variants[name]

    def __delitem__(self, name):
        del self.variants[name]

    def _get_parser(self):
        return productmd.common.SortedConfigParser()

    def parse_file(self, f):
        # parse file, return parser or dict with data
        f.seek(0)
        parser = productmd.common.SortedConfigParser()
        parser.read_file(f)
        return parser

    def build_file(self, parser, f):
        # build file from parser or dict with data
        parser.write(f)

    def serialize(self, parser, main_variant=None):
        self.validate()
        self.header.serialize(parser)
        self.release.serialize(parser)
        if self.release.is_layered:
            self.base_product.serialize(parser)
        self.tree.serialize(parser)
        self.variants.serialize(parser)
        self.checksums.serialize(parser)
        self.images.serialize(parser)
        self.stage2.serialize(parser)
        self.media.serialize(parser)
        # HACK: generate [general] section for compatibility
        general = General(self)
        general.serialize(parser, main_variant=main_variant)

    def deserialize(self, parser):
        self.header.deserialize(parser)
        self.release.deserialize(parser)
        if self.release.is_layered:
            self.base_product.deserialize(parser)
        self.tree.deserialize(parser)
        self.variants.deserialize(parser)
        self.checksums.deserialize(parser)
        self.images.deserialize(parser)
        self.stage2.deserialize(parser)
        self.media.deserialize(parser)
        self.validate()
        self.header.set_current_version()
        return parser

    def dump(self, f, main_variant=None):
        """
        Dump data to a file.

        :param f: file-like object or path to file
        :param main_variant: a main variant's name of a treeinfo
        :type f: file or str
        :type main_variant: str
        """
        self.validate()
        with productmd.common.open_file_obj(f, "w") as f:
            parser = self._get_parser()
            self.serialize(parser, main_variant=main_variant)
            self.build_file(parser, f)


class Header(productmd.common.Header):

    def serialize(self, parser):
        self.validate()
        parser.add_section(self._section)
        # write *current* version, because format gets converted on save
        parser.set(self._section, "version", ".".join([str(i) for i in productmd.common.VERSION]))
        parser.set(self._section, "type", self.metadata_type)

    def deserialize(self, parser):
        if parser.has_option(self._section, "version"):
            self.version = parser.get(self._section, "version")
            if self.version_tuple >= (1, 1):
                metadata_type = parser.get(self._section, "type")
                if metadata_type != self.metadata_type:
                    raise ValueError("Invalid metadata type '%s', expected '%s'" % (metadata_type, self.metadata_type))
        self.validate()


class BaseProduct(productmd.common.MetadataBase):
    """
    :class:`.BaseProduct` provides information about operating system a :class:`.Release` runs on.
    """

    def __init__(self, metadata):
        super(BaseProduct, self).__init__()
        self._section = "base_product"
        self._metadata = metadata
        self.name = None                #: (*str*) -- base product name, for example: "Fedora", "Red Hat Enterprise Linux"
        self.short = None               #: (*str*) -- base product short name, for example: "F", "RHEL"
        self.version = None             #: (*str*) -- base product *major* version, for example: "21", "7"

    def _validate_name(self):
        self._assert_type("name", list(six.string_types))

    def _validate_version(self):
        self._assert_type("version", list(six.string_types))
        if re.match(r'^\d', self.version):
            self._assert_matches_re("version", [r"^\d+(\.\d+)*$"])

    def _validate_short(self):
        self._assert_type("short", list(six.string_types))

    def serialize(self, parser):
        self.validate()
        parser.add_section(self._section)
        parser.set(self._section, "name", self.name)
        parser.set(self._section, "version", self.version)
        parser.set(self._section, "short", self.short)

    def deserialize(self, parser):
        self.name = parser.get(self._section, "name")
        self.version = parser.get(self._section, "version")
        self.short = parser.get(self._section, "short")
        self.validate()


class Release(BaseProduct):

    def __init__(self, metadata):
        super(Release, self).__init__(metadata)
        self._section = "release"
        self.name = None                #: (*str*) -- release name, for example: "Fedora", "Red Hat Enterprise Linux", "Spacewalk"
        self.short = None               #: (*str*) -- release short name, for example: "F", "RHEL", "Spacewalk"
        self.version = None             #: (*str*) -- release version, for example: "21", "7.0", "2.1"
        self.is_layered = False         #: (*bool*) -- typically False for an operating system, True otherwise

    def _validate_is_layered(self):
        self._assert_type("is_layered", [bool])

    def serialize(self, parser):
        self.validate()
        parser.add_section(self._section)
        parser.set(self._section, "name", self.name)
        parser.set(self._section, "version", self.version)
        parser.set(self._section, "short", self.short)
        if self.is_layered:
            parser.set(self._section, "is_layered", "true")

    def deserialize(self, parser):
        if self._metadata.header.version_tuple == (0, 0):
            self.deserialize_0_0(parser)
        elif self._metadata.header.version_tuple <= (0, 3):
            self.deserialize_0_3(parser)
        else:
            self.deserialize_1_0(parser)
        self.validate()

    # pre-productmd treeinfos
    def deserialize_0_0(self, parser):
        self.name = parser.get("general", "family")
        self.version = parser.get("general", "version")
        for i in re.split(r"[-_]", self.version):
            if re.match(r"^\d+(\.\d+)*$", i):
                self.version = i
        if self.name.startswith("Red Hat Enterprise Linux"):
            self.name = "Red Hat Enterprise Linux"
            self.short = "RHEL"
        elif self.name == "Subscription Asset Manager":
            self.short = "SAM"
        elif self.name == "Red Hat Storage":
            self.short = "RHS"
        elif self.name == "JBEAP":
            self.short = "JBEAP"
        elif self.name == "Red Hat Storage Software Appliance":
            self.short = "SSA"
        elif self.name.startswith("Fedora"):
            self.name = "Fedora"
            self.short = "Fedora"
        elif self.name.startswith("CentOS"):
            self.name = "CentOS"
            self.short = "CentOS"
        elif self.name.startswith("EulerOS"):
            self.name = "EulerOS"
            self.short = "EulerOS"
        else:
            self.short = ""

    def deserialize_0_3(self, parser):
        self.name = parser.get("product", "name")
        self.version = parser.get("product", "version")
        self.short = parser.get("product", "short")
        if parser.has_option("product", "is_layered"):
            self.is_layered = parser.getboolean("product", "is_layered")

    def deserialize_1_0(self, parser):
        self.name = parser.get(self._section, "name")
        self.version = parser.get(self._section, "version")
        if parser.has_option(self._section, "short"):
            self.short = parser.get(self._section, "short")
        else:
            self.short = self.name
        if parser.has_option(self._section, "is_layered"):
            self.is_layered = parser.getboolean(self._section, "is_layered")

    @property
    def major_version(self):
        """
        Version string without the last part.
        For example: version == 1.2.0 -> major_version == 1.2
        """
        if self.version is None:
            return None
        return productmd.common.get_major_version(self.version)

    @property
    def minor_version(self):
        """
        Last part of the version string.
        For example: version == 1.2.0 -> minor_version == 0
        """
        if self.version is None:
            return None
        return productmd.common.get_minor_version(self.version)


# Note: [tree]/variants is read/written in the Variants class
class Tree(productmd.common.MetadataBase):

    def __init__(self, _metadata):
        super(Tree, self).__init__()
        self._section = "tree"
        self._metadata = _metadata
        self.arch = None                #: (*str*) -- tree architecture, for example x86_64
        self.build_timestamp = None     #: (*int*, *float*) -- tree build time timestamp; format: unix time
        self.platforms = set()          #: (*set(str)*), supported platforms; for example x86_64,xen

    def _validate_arch(self):
        self._assert_type("arch", list(six.string_types))
        self._assert_not_blank("arch")

    def _validate_build_timestamp(self):
        self._assert_type("build_timestamp", list(six.integer_types) + [float])
        self._assert_not_blank("build_timestamp")

    def serialize(self, parser):
        self.validate()
        parser.add_section(self._section)
        parser.set(self._section, "arch", self.arch)
        parser.set(self._section, "platforms", ",".join(sorted(self.platforms | set([self.arch]))))
        parser.set(self._section, "build_timestamp", str(self.build_timestamp))

    def deserialize(self, parser):
        if self._metadata.header.version_tuple == (0, 0):
            self.deserialize_0_0(parser)
        else:
            self.deserialize_1_0(parser)
        self.validate()

    def deserialize_0_0(self, parser):
        self.arch = parser.get("general", "arch")
        self.platforms.add(self.arch)

        if self.arch in parser.sections():
            self.platforms.update([i for i in parser.get(self.arch, "platforms").split(",") if i])
        for i in parser.sections():
            if not i.startswith("images-"):
                continue
            i = i[7:]
            if i != self.arch and i.endswith("-%s" % self.arch):
                i = i[:-len(self.arch)-1]
            self.platforms.add(i)

        if parser.has_option("general", "timestamp"):
            self.build_timestamp = int(parser.getfloat("general", "timestamp"))
        else:
            self.build_timestamp = -1

    def deserialize_1_0(self, parser):
        section = self._section if parser.has_section(self._section) else "general"

        self.arch = parser.get(section, "arch")
        self.platforms = set([i for i in parser.get(section, "platforms").split(",") if i])
        if section == self._section:
            self.build_timestamp = int(parser.getfloat(self._section, "build_timestamp"))
        else:
            self.build_timestamp = -1


class Variants(productmd.composeinfo.VariantBase):
    def __init__(self, metadata):
        super(Variants, self).__init__(metadata)
        self._metadata = metadata

    def __len__(self):
        return len(self.variants)

    def serialize(self, parser):
        self.validate()

        # variant UIDs *should* be identical to IDs at the top level,
        # but sometimes they can differ (Server-optional)
        variant_ids = sorted([i.uid for i in self.variants.values()])

        parser.set("tree", "variants", ",".join(sorted(variant_ids)))

        for variant in self.variants.values():
            variant.serialize(parser)

    def deserialize(self, parser):
        # variant UIDs should be identical to IDs at the top level
        if self._metadata.header.version_tuple == (0, 0):
            variant_ids = self.deserialize_0_0(parser)
        else:
            variant_ids = self.deserialize_1_0(parser)

        for variant_id in variant_ids:
            variant = Variant(self._metadata)
            variant.deserialize(parser, variant_id)
            # handle cases when top-level ID != UID, like $variant-optional
            self.add(variant, variant_id=variant.uid)

        self.validate()

    def deserialize_0_0(self, parser):
        if not parser.has_option("general", "variant") and parser.get("general", "family") == "Red Hat Enterprise Linux Server":
            variant_ids = "Server"
        elif not parser.has_option("general", "variant") and parser.get("general", "family") == "Red Hat Enterprise Linux Client":
            variant_ids = "Client"
        elif not parser.has_option("general", "variant") and parser.get("general", "family") == "CentOS":
            variant_ids = "CentOS"
        else:
            variant_ids = parser.get("general", "variant")
        if variant_ids:
            variant_ids = [variant_ids]
        else:
            variant_ids = [i[8:] for i in parser.sections() if i.startswith("variant-")]
            variant_ids = [i for i in variant_ids if "-" not in i]  # we want only top-level variants
        if not variant_ids:
            variant_ids = [self._metadata.release.short]
        return variant_ids

    def deserialize_1_0(self, parser):
        if not parser.has_option("tree", "variants"):
            return []
        variant_ids = [i for i in parser.get("tree", "variants").split(",")]
        return variant_ids


class VariantPaths(productmd.common.MetadataBase):
    """
    This class stores paths for a variant in a tree.
    All paths are relative to .treeinfo location.

    **Binary**

        * **packages** -- directory with binary RPMs
        * **repository** -- YUM repository with binary RPMs

    **Source**

        * **source_packages** -- directory with source RPMs
        * **source_repository** -- YUM repository with source RPMs

    **Debug**

        * **debug_packages** -- directory with debug RPMs
        * **debug_repository** -- YUM repository with debug RPMs

    **Others**
        * **identity** -- path to a pem file which identifies a product

    Example::

        variant = ...
        variant.paths.packages = "Packages"
        variant.paths.repository = "."
    """

    def __init__(self, variant):
        self._variant = variant
        self._metadata = self._variant._metadata

        self._fields = [
            # binary
            "packages",
            "repository",

            # source
            "source_packages",
            "source_repository",

            # debug
            "debug_packages",
            "debug_repository",

            # others
            "identity",
        ]

        for name in self._fields:
            setattr(self, name, None)

    def deserialize(self, parser):
        if self._metadata.header.version_tuple == (0, 0):
            self.deserialize_0_0(parser)
        elif self._metadata.header.version_tuple <= (0, 3):
            self.deserialize_0_3(parser)
        else:
            self.deserialize_1_0(parser)

        self.validate()

    # pre-productmd treeinfos
    def deserialize_0_0(self, parser):
        # repository
        lookup = [
            ("variant-%s" % self._variant.id, "repository"),
            ("addon-%s" % self._variant.id, "repository"),
            ("general", "repository"),
        ]
        self.repository = parser.option_lookup(lookup, ".")

        # remove /repodata from repository path
        self.repository = self.repository.rstrip("/") or "."
        if self.repository.endswith("/repodata"):
            self.repository = self.repository[:-9]

        if self.repository == ".":
            if self._metadata.release.short == "RHEL" and self._metadata.release.major_version in ("5", "6"):
                # HACK: repo dirs named by variants on RHEL 5, 6
                self.repository = self._variant.id
            if self._metadata.release.short == "RHEL" and self._metadata.release.major_version in ("3", "4"):
                # HACK: no repos on RHEL 3, 4
                self.repository = None

        # packages
        lookup = [
            ("variant-%s" % self._variant.uid, "packages"),
            ("variant-%s" % self._variant.uid, "packagedir"),
            ("addon-%s" % self._variant.uid, "packages"),
            ("addon-%s" % self._variant.uid, "packagedir"),
            ("variant-%s" % self._variant.id, "packages"),
            ("variant-%s" % self._variant.id, "packagedir"),
            ("addon-%s" % self._variant.id, "packages"),
            ("addon-%s" % self._variant.id, "packagedir"),
            ("general", "packages"),
            ("general", "packagedir"),
            ("general", "packagedirs"),
        ]
        self.packages = parser.option_lookup(lookup, self.repository) or ""
        self.packages = self.packages.rstrip("/") or "."

        if self._metadata.release.short == "RHEL" and self._metadata.release.major_version == "5":
            # HACK: RHEL 5
            self.packages = self._variant.id
        elif self._metadata.release.short == "RHEL" and self._metadata.release.major_version in ("3", "4"):
            # HACK: RHEL 3, 4
            self.packages = "RedHat/RPMS"
        elif self._metadata.release.short == "Fedora":
            # HACK: replace empty packagedir with "Packages" on Fedora
            if self.packages == ".":
                self.packages = "Packages"

        if self._metadata.tree.arch == "src":
            self.source_packages = self.packages
            self.source_repository = self.repository
            self.packages = None
            self.repository = None

        # identity
        lookup = [
            ("variant-%s" % self._variant.uid, "identity"),
            ("addon-%s" % self._variant.uid, "identity"),
            ("variant-%s" % self._variant.id, "identity"),
            ("addon-%s" % self._variant.id, "identity"),
            ("general", "identity"),
        ]
        self.identity = parser.option_lookup(lookup, None)

    def deserialize_0_3(self, parser):
        for field in self._fields:
            lookup = [
                ("variant-%s" % self._variant.uid, field),
                ("variant-%s" % self._variant.id, field),
                ("addon-%s" % self._variant.uid, field),
                ("addon-%s" % self._variant.id, field),
            ]
            value = parser.option_lookup(lookup, None)
            setattr(self, field, value)

        if self._metadata.tree.arch == "src":
            self.source_packages = self.packages
            self.source_repository = self.repository
            self.packages = None
            self.repository = None

    def deserialize_1_0(self, parser):
        for field in self._fields:
            if parser.has_option(self._variant._section, field):
                value = parser.get(self._variant._section, field)
            else:
                value = None
            setattr(self, field, value)

    def serialize(self, parser):
        self.validate()
        for field in self._fields:
            value = getattr(self, field, None)
            if value is not None:
                parser.set(self._variant._section, field, value)


class Variant(productmd.composeinfo.VariantBase):
    def __init__(self, metadata):
        super(Variant, self).__init__(metadata)

        # variant details
        self.id = None          #: (*str*) -- variant ID, for example "Server", "optional"
        self.uid = None         #: (*str*) -- variant UID ($parent_UID.$ID), for example "Server", "Server-optional"
        self.name = None        #: (*str*) -- variant name, for example "Server"
        self.type = None        #: (*str*) -- "variant", "addon", "optional"

        self.parent = None                  #: (:class:`.Variant` or *None*) -- reference to parent :class:`.Variant`
        self.variants = {}                  #: (*dict*) :class:`.Variant`
        self.paths = VariantPaths(self)     #: (:class:`.VariantPaths`) -- relative paths to repositories, packages, etc.

    def __str__(self):
        return self.uid

    def __delitem__(self, name):
        # remove repomd.xml from checksums (but only if exists)
        repository = self[name].paths.repository + "/repodata/repomd.xml"
        super(Variant, self).__delitem__(name)
        if repository in self._metadata.checksums.checksums.keys():
            del self._metadata.checksums.checksums[repository]

    @property
    def arch(self):
        return self._metadata.tree.arch

    @property
    def _section(self):
        if self.type == "addon":
            section = "addon-" + self.uid
        else:
            section = "variant-" + self.uid
        return section

    def _validate_id(self):
        self._assert_type("id", [str])
        if "-" in self.id:
            raise ValueError("Invalid character '-' in variant ID: %s" % self.id)

    def _validate_uid(self):
        if self.parent:
            uid = "%s-%s" % (self.parent.uid, self.id)
        else:
            uid = self.uid
        if self.uid != uid:
            raise ValueError("UID '%s' doesn't align with parent UID '%s'" % (self.uid, uid))

    def _validate_type(self):
        self._assert_value("type", VARIANT_TYPES)

    def deserialize(self, parser, uid, addon=False):
        if not uid:
            raise ValueError("Invalid variant UID value: %s" % uid)

        self.uid = uid
        if addon:
            self.type = "addon"

        # variant details
        if self._metadata.header.version_tuple == (0, 0):
            self.deserialize_0_0(parser, uid, addon=addon)
        elif self._metadata.header.version_tuple <= (0, 3):
            self.deserialize_0_3(parser, uid, addon=addon)
        else:
            self.deserialize_1_0(parser, uid, addon=addon)

        self.paths.deserialize(parser)

    # pre-productmd treeinfo
    def deserialize_0_0(self, parser, uid, addon=False):
        # id, uid
        self.id = uid.split("-")[-1]
        self.uid = uid

        # variant type and section
        sections = [
            "addon-" + self.uid,
            "addon-" + self.id,
            "variant-" + self.uid,
            "variant-" + self.id,
        ]
        for section in sections:
            if parser.has_option(section, "type"):
                self.type = parser.get(section, "type")
                break
            if parser.has_section(section):
                if "addon" in section:
                    self.type = "addon"
                elif "optional" in self.id:
                    self.type = "optional"
                else:
                    self.type = "variant"
                break

        if not self.type:
            # no variant/addon section, fallback to general
            if addon:
                self.type = "addon"
            else:
                self.type = "variant"
            self.name = self._metadata.release.name
            self.uid = uid
            self.id = uid.rsplit("-")[-1]

        # name
        if parser.has_option(section, "name"):
            self.name = parser.get(section, "name")
        else:
            self.name = self.id

        if self.type == "variant":
            lookup = [
                (section, "addons"),
                (section, "variants"),
                ("general", "addons"),
            ]
            addons = parser.option_lookup(lookup, "").split(",")
            addons = [i for i in addons if i]
            if self._metadata.release.short == "RHEL" and self._metadata.release.major_version == "5":
                # workaround for RHEL 5 - add addons
                if self.uid == "Client":
                    addons = ["VT", "Workstation"]
                if self.uid == "Server":
                    if self.arch in ("i386", "ia64", "x86_64"):
                        addons = ["Cluster", "ClusterStorage", "VT"]
                    elif self.arch == "ppc":
                        if self._metadata.release.minor_version == "0":
                            # no addons on RHEL 5.0 Server.ppc
                            addons = []
                        else:
                            addons = ["Cluster", "ClusterStorage"]
                    elif self.arch == "s390x":
                        addons = []
            for addon_id in addons:
                addon_uid = addon_id
                if not addon_uid.startswith("%s-" % self.uid):
                    addon_uid = "%s-%s" % (self.uid, addon_uid)
                addon = Variant(self._metadata)
                addon.deserialize(parser, addon_uid)
                # HACK: for RHEL 5 addons
                addon.type = "addon"
                self.add(addon)

    def deserialize_0_3(self, parser, uid, addon=False):
        section = "variant-%s" % uid
        if not parser.has_section(section):
            section = "addon-%s" % uid
        self.id = parser.get(section, "id")
        self.uid = parser.get(section, "uid")
        self.name = parser.get(section, "name")
        self.type = parser.get(section, "type")

        # child addons
        addons = ""
        if parser.has_option(section, "addons"):
            addons = parser.get(section, "addons")
        elif parser.has_option(section, "variants"):
            addons = parser.get(section, "variants")
        if addons:
            variant_uids = [i for i in addons.split(",") if i]
            for variant_uid in variant_uids:
                variant = Variant(self._metadata)
                variant.deserialize(parser, variant_uid, addon=True)
                self.add(variant)

    def deserialize_1_0(self, parser, uid, addon=False):
        self.id = parser.get(self._section, "id")
        self.uid = parser.get(self._section, "uid")
        self.name = parser.get(self._section, "name")
        self.type = parser.get(self._section, "type")

        # child addons
        if parser.has_option(self._section, "addons"):
            variant_uids = [i for i in parser.get(self._section, "addons").split(",") if i]
            for variant_uid in variant_uids:
                variant = Variant(self._metadata)
                variant.deserialize(parser, variant_uid, addon=True)
                self.add(variant)

    def serialize(self, parser):
        self.validate()
#        print "SERIALIZE", self._section, self.type
        parser.add_section(self._section)

        # variant details
        parser.set(self._section, "id", self.id)
        parser.set(self._section, "uid", self.uid)
        parser.set(self._section, "name", self.name)
        parser.set(self._section, "type", self.type)

        # paths
        self.paths.serialize(parser)

        # parent
        if self.parent:
            parser.set(self._section, "parent", self.parent.uid)

        # child variants
        variant_uids = set()
        for variant in self.variants.values():
            variant.serialize(parser)
            variant_uids.add(variant.uid)
        if variant_uids:
            parser.set(self._section, "addons", ",".join(sorted(variant_uids)))


class Images(productmd.common.MetadataBase):

    def __init__(self, metadata):
        super(Images, self).__init__()
        self._metadata = metadata
        self.images = {}

    def __getitem__(self, platform):
        return self.images[platform]

    def _fix_path(self, path):
        if self._metadata.header.version_tuple == (0, 0):
            if path.startswith("/"):
                if "/os/" in path:
                    path = path[path.find("/os/")+4:]
                else:
                    path = path.lstrip("/")
        return path

    @property
    def platforms(self):
        """Return all platforms with available images"""
        return sorted(self.images.keys())

    def serialize(self, parser):
        if not self.images:
            return
        self.validate()
        for platform in self.images:
            section = "images-%s" % platform
            parser.add_section(section)
            for image, path in self.images[platform].items():
                parser.set(section, image, path)

    def deserialize(self, parser):
        for section in parser.sections():
            if not section.startswith("images-"):
                continue
            platform = section[7:]
            if platform != self._metadata.tree.arch and platform.endswith("-%s" % self._metadata.tree.arch):
                platform = platform[:-len(self._metadata.tree.arch)-1]
            self.images[platform] = {}
            for image, path in parser.items(section):
                path = parser.get(section, image)  # re-read path to populate 'seen' records in tests
                self.images[platform][image] = self._fix_path(path)
        self.validate()

    def _validate_image_paths(self):
        for platform in self.images:
            for image, path in self.images[platform].items():
                if path.startswith("/"):
                    raise ValueError("Only relative paths are allowed for images: %s" % path)

    def _validate_platforms(self):
        for platform in self.platforms:
            if platform not in self._metadata.tree.platforms:
                raise ValueError("Platform has images but is not referenced in platform list: %s, %s"
                                 % (platform, self._metadata.tree.platforms))


class Stage2(productmd.common.MetadataBase):
    def __init__(self, metadata):
        super(Stage2, self).__init__()
        self._section = "stage2"
        self._metadata = metadata
        self.mainimage = None           #: (*str*) -- relative path to Anaconda stage2 image
        self.instimage = None           #: (*str*) -- relative path to Anaconda instimage (obsolete)

    def __getitem__(self, name):
        getattr(self, name)

    def _fix_path(self, path):
        if self._metadata.header.version_tuple == (0, 0):
            if path.startswith("/"):
                if "/os/" in path:
                    path = path[path.find("/os/")+4:]
                else:
                    path = path.lstrip("/")
        return path

    def serialize(self, parser):
        if not self.mainimage and not self.instimage:
            return
        self.validate()
        parser.add_section(self._section)
        if self.mainimage:
            parser.set(self._section, "mainimage", self.mainimage)
        if self.instimage:
            parser.set(self._section, "instimage", self.instimage)

    def deserialize(self, parser):
        if parser.has_option(self._section, "mainimage"):
            self.mainimage = self._fix_path(parser.get(self._section, "mainimage"))
        if parser.has_option(self._section, "instimage"):
            self.instimage = self._fix_path(parser.get(self._section, "instimage"))
        self.validate()

    def _validate_mainimage(self):
        if self.mainimage:
            self._assert_type("mainimage", list(six.string_types))
            if self.mainimage.startswith("/"):
                raise ValueError("Only relative paths are allowed for images: %s" % self.mainimage)

    def _validate_platforms(self):
        pass


class Checksums(productmd.common.MetadataBase):

    def __init__(self, metadata):
        super(Checksums, self).__init__()
        self._section = "checksums"
        self._metadata = metadata
        self.checksums = {}

    def __getitem__(self, name):
        return self.checksums[name]

    def _fix_path(self, path):
        if self._metadata.header.version_tuple == (0, 0):
            if path.startswith("/"):
                if "/os/" in path:
                    path = path[path.find("/os/")+4:]
                else:
                    path = path.lstrip("/")
        return path

    def serialize(self, parser):
        self.validate()
        if not self.checksums:
            return
        parser.add_section(self._section)
        for path, (checksum_type, checksum) in self.checksums.items():
            parser.set(self._section, path, "%s:%s" % (checksum_type, checksum))

    def deserialize(self, parser):
        if parser.has_section(self._section):
            for path, value in parser.items(self._section):
                path = self._fix_path(path)
                if ":" not in value:
                    if len(value) == 32:
                        checksum_type, checksum = "md5", value
                    elif len(value) == 40:
                        checksum_type, checksum = "sha1", value
                    elif len(value) == 64:
                        checksum_type, checksum = "sha256", value
                else:
                    checksum_type, checksum = value.split(":")
                self.checksums[path] = (checksum_type, checksum)
        self.validate()

    def _check_checksum_paths(self):
        for path in self.checksums:
            if path.startswith("/"):
                raise ValueError("Only relative paths are allowed for checksums: %s" % path)

    def add(self, relative_path, checksum_type, checksum_value=None, root_dir=None):
        if relative_path.startswith("/"):
            raise ValueError("Relative path expected: %s" % relative_path)
        relative_path = os.path.normpath(relative_path)
        if not checksum_value:
            absolute_path = os.path.join(root_dir, relative_path)
            checksum_value = compute_checksum(absolute_path, checksum_type)
        self.checksums[relative_path] = [checksum_type, checksum_value]


class Media(productmd.common.MetadataBase):

    def __init__(self, metadata):
        super(Media, self).__init__()
        self._section = "media"
        self._metadata = metadata
        self.discnum = None             #: disc number
        self.totaldiscs = None          #: number of discs in media set

    def _validate_discnum(self):
        self._assert_type("discnum", list(six.integer_types) + [type(None)])

    def _validate_totaldiscs(self):
        self._assert_type("totaldiscs", list(six.integer_types) + [type(None)])

    def serialize(self, parser):
        if not self.discnum and not self.totaldiscs:
            return
        self.validate()
        parser.add_section(self._section)
        parser.set(self._section, "discnum", str(int(self.discnum)))
        parser.set(self._section, "totaldiscs", str(int(self.totaldiscs)))

    def deserialize(self, parser):
        if self._metadata.header.version_tuple == (0, 0):
            self.deserialize_0_0(parser)
        else:
            self.deserialize_1_0(parser)
        self.validate()

    def deserialize_0_0(self, parser):
        if parser.has_option("general", "discnum") or parser.has_option("general", "totaldiscs"):
            if parser.has_option("general", "discnum"):
                self.discnum = parser.getint("general", "discnum")
            else:
                self.discnum = 1
            if parser.has_option("general", "totaldiscs"):
                self.totaldiscs = parser.getint("general", "totaldiscs")
            else:
                self.totaldiscs = self.discnum

    def deserialize_1_0(self, parser):
        if parser.has_section(self._section):
            self.discnum = parser.getint(self._section, "discnum")
            self.totaldiscs = parser.getint(self._section, "totaldiscs")


class General(productmd.common.MetadataBase):

    def __init__(self, metadata):
        super(General, self).__init__()
        self._section = "general"
        self._metadata = metadata

    def serialize(self, parser, main_variant=None):
        parser.add_section(self._section)
        parser.set(self._section, "; WARNING.0", "This section provides compatibility with pre-productmd treeinfos.")
        parser.set(self._section, "; WARNING.1", "Read productmd documentation for details about new format.")
        parser.set(self._section, "name", "%s %s" % (self._metadata.release.name, self._metadata.release.version))
        parser.set(self._section, "family", self._metadata.release.name)
        parser.set(self._section, "version", self._metadata.release.version)

        parser.set(self._section, "arch", self._metadata.tree.arch)
        parser.set(self._section, "platforms", ",".join(sorted(self._metadata.tree.platforms | set([self._metadata.tree.arch]))))
        parser.set(self._section, "timestamp", str(int(self._metadata.tree.build_timestamp)))

        variants = list(self._metadata.variants)
        variants.sort()
        parser.set(self._section, "variants", ",".join(variants))

        # HACK: if there are more variants and main_variant is None,
        # use the first variant if
        if main_variant is None:
            variant = variants[0]
        else:
            variant = main_variant
        parser.set(self._section, "variant", variant)

        # packages
        if self._metadata.variants[variant].paths.packages is not None:
            parser.set(self._section, "packagedir", self._metadata.variants[variant].paths.packages)
        elif self._metadata.tree.arch == "src" and self._metadata.variants[variant].paths.source_packages is not None:
            parser.set(self._section, "packagedir", self._metadata.variants[variant].paths.source_packages)

        # repository
        if self._metadata.variants[variant].paths.repository is not None:
            parser.set(self._section, "repository", self._metadata.variants[variant].paths.repository)
        elif self._metadata.tree.arch == "src" and self._metadata.variants[variant].paths.source_repository is not None:
            parser.set(self._section, "repository", self._metadata.variants[variant].paths.source_repository)
