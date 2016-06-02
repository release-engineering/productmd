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
This module provides classes for manipulating images.json files.
images.json files provide details about images included in composes.
"""


import productmd.common
from productmd.common import Header
from productmd.composeinfo import Compose

import six


__all__ = (
    "Image",
    "Images",
    "SUPPORTED_IMAGE_TYPES",
    "SUPPORTED_IMAGE_FORMATS",
)


#: supported image types
SUPPORTED_IMAGE_TYPES = ['boot', 'cd', 'docker', 'dvd', 'ec2', 'kvm', 'live',
                         'netinst', 'p2v', 'qcow2', 'raw-xz', 'rescue', 'vagrant-libvirt', 'vagrant-virtualbox']

#: supported image formats, they match with file suffix
SUPPORTED_IMAGE_FORMATS = ['iso', 'qcow', 'qcow2', 'raw', 'raw.xz', 'rhevm.ova',
                           'sda.raw', 'tar.gz', 'tar.xz', 'vagrant-libvirt.box', 'vagrant-virtualbox.box',
                           'vdi', 'vmdk', 'vmx', 'vsphere.ova']


class Images(productmd.common.MetadataBase):
    def __init__(self):
        super(Images, self).__init__()
        self.header = Header(self, "productmd.images")
        self.compose = Compose(self)
        self.images = {}

    def __getitem__(self, variant):
        return self.images[variant]

    def __delitem__(self, variant):
        del self.images[variant]

    def serialize(self, parser):
        data = parser
        self.header.serialize(data)
        data["payload"] = {}
        data["payload"]["images"] = {}
        self.compose.serialize(data["payload"])
        for variant in self.images:
            for arch in self.images[variant]:
                for image_obj in self.images[variant][arch]:
                    images = data["payload"]["images"].setdefault(variant, {}).setdefault(arch, [])
                    image_obj.serialize(images)
                    images.sort(key=lambda x: x["path"])
        return data

    def deserialize(self, data):
        self.header.deserialize(data)
        self.compose.deserialize(data["payload"])
        for variant in data["payload"]["images"]:
            for arch in data["payload"]["images"][variant]:
                for image in data["payload"]["images"][variant][arch]:
                    image_obj = Image(self)
                    image_obj.deserialize(image)
                    if self.header.version_tuple <= (1, 1):
                        self._add_1_1(data, variant, arch, image_obj)
                    else:
                        self.add(variant, arch, image_obj)
        self.header.set_current_version()

    def _add_1_1(self, data, variant, arch, image):
        if arch == "src":
            # move src under binary arches
            for variant_arch in data["payload"]["images"][variant]:
                if variant_arch == "src":
                    continue
                self.add(variant, variant_arch, image)
        else:
            self.add(variant, arch, image)

    def add(self, variant, arch, image):
        """
        Assign an :class:`.Image` object to variant and arch.

        :param variant: compose variant UID
        :type  variant: str
        :param arch:    compose architecture
        :type  arch:    str
        :param image:   image
        :type  image:   :class:`.Image`
        """

        if arch not in productmd.common.RPM_ARCHES:
            raise ValueError("Arch not found in RPM_ARCHES: %s" % arch)
        if arch in ["src", "nosrc"]:
            raise ValueError("Source arch is not allowed. Map source files under binary arches.")
        self.images.setdefault(variant, {}).setdefault(arch, set()).add(image)


class Image(productmd.common.MetadataBase):
    def __init__(self, parent):
        super(Image, self).__init__()
        self.parent = parent
        self.path = None                #: (*str*) -- relative path to an image, for example: "Server/x86_64/iso/boot.iso"
        self.mtime = None               #: (*int*) -- image mtime
        self.size = None                #: (*int*) -- image size
        self.volume_id = None           #: (*str*) --
        self.type = None                #: (*str*) --
        self.format = None              #: (*str*) -- Release name, for example: "Fedora", "Red Hat Enterprise Linux"
        self.arch = None                #: (*str*) -- image architecture, for example: "x86_64", "src"
        self.disc_number = None         #: (*int*) -- Release name, for example: "Fedora", "Red Hat Enterprise Linux"
        self.disc_count = None          #: (*int*) -- Release name, for example: "Fedora", "Red Hat Enterprise Linux"
        self.checksums = {}             #: (*str*) -- Release name, for example: "Fedora", "Red Hat Enterprise Linux"
        self.implant_md5 = None         #: (*str* or *None*) -- value of implanted md5
        self.bootable = False           #: (*bool=False*) --
        self.subvariant = None          #: (*str*) -- image contents, may be same as variant or e.g. 'KDE', 'LXDE'

    def __repr__(self):
        return "<Image:{0.path}:{0.format}:{0.arch}>".format(self)

    def _validate_path(self):
        self._assert_type("path", list(six.string_types))
        self._assert_not_blank("path")

    def _validate_mtime(self):
        self._assert_type("mtime", list(six.integer_types))

    def _validate_size(self):
        self._assert_type("size", list(six.integer_types))
        self._assert_not_blank("size")

    def _validate_volume_id(self):
        self._assert_type("volume_id", [type(None)] + list(six.string_types))
        if self.volume_id is not None:
            self._assert_not_blank("volume_id")

    def _validate_type(self):
        self._assert_type("type", list(six.string_types))
        self._assert_value("type", SUPPORTED_IMAGE_TYPES)

    def _validate_format(self):
        self._assert_type("format", list(six.string_types))
        self._assert_value("format", SUPPORTED_IMAGE_FORMATS)

    def _validate_arch(self):
        self._assert_type("arch", list(six.string_types))
        self._assert_not_blank("arch")

    def _validate_disc_number(self):
        self._assert_type("disc_number", list(six.integer_types))

    def _validate_disc_count(self):
        self._assert_type("disc_count", list(six.integer_types))

    def _validate_checksums(self):
        self._assert_type("checksums", [dict])
        self._assert_not_blank("checksums")

    def _validate_implant_md5(self):
        self._assert_type("implant_md5", [type(None)] + list(six.string_types))
        if self.implant_md5 is not None:
            self._assert_matches_re("implant_md5", [r"^[a-z0-9]{32}$"])

    def _validate_bootable(self):
        self._assert_type("bootable", [bool])

    def _validate_subvariant(self):
        self._assert_type("subvariant", list(six.string_types))

    def serialize(self, parser):
        data = parser
        self.validate()
        result = {
            "path": self.path,
            "mtime": self.mtime,
            "size": self.size,
            "volume_id": self.volume_id,
            "type": self.type,
            "format": self.format,
            "arch": self.arch,
            "disc_number": self.disc_number,
            "disc_count": self.disc_count,
            "checksums": self.checksums,
            "implant_md5": self.implant_md5,
            "bootable": self.bootable,
            "subvariant": self.subvariant,
        }
        data.append(result)

    def deserialize(self, data):
        self.path = data["path"]
        self.mtime = int(data["mtime"])
        self.size = int(data["size"])
        self.volume_id = data["volume_id"]
        self.type = data["type"]
        self.format = data.get("format", "iso")
        self.arch = data["arch"]
        self.disc_number = int(data["disc_number"])
        self.disc_count = int(data["disc_count"])
        self.checksums = data["checksums"]
        self.implant_md5 = data["implant_md5"]
        self.bootable = bool(data["bootable"])
        if self.parent.header.version_tuple <= (1, 0):
            self.subvariant = data.get("subvariant", "")
        else:
            # 1.1+
            self.subvariant = data["subvariant"]
        self.validate()

    def add_checksum(self, root, checksum_type, checksum_value):
        if checksum_type in self.checksums:
            if checksum_value and checksum_value != self.checksums[checksum_type]:
                raise ValueError("Existing and added checksums do not match: %s vs %s" % (self.checksums[checksum_type], checksum_value))
            return self.checksums[checksum_type]

        self.checksums[checksum_type] = checksum_value
        return checksum_value
