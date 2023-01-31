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

Example::
  import productmd.compose
  compose = productmd.compose.Compose("/path/to/compose")

  # Print the entire dict that maps all variants, arches, and images for this
  # compose:
  print(compose.images.images)

  # Find all the qcow2 images in this compose:
  qcow2s = set()

  for variant in compose.images.images:
      for arch in compose.images.images[variant]:
          for images in compose.images.images[variant].values():
              if image.type == 'qcow2':
                  qcow2s.add(image)

  print(qcow2s)

  # ... prints the set of qcow2 images in all our variants:
  [<Image:Server-RT/x86_64/images/rhel-kvm-rt-image-7.6-220.x86_64.qcow2:qcow2:x86_64>,
 <Image:Server/x86_64/images/rhel-guest-image-7.6-210.x86_64.qcow2:qcow2:x86_64>,
 <Image:Server/ppc64le/images/rhel-guest-image-7.6-210.ppc64le.qcow2:qcow2:ppc64le>]

"""


import productmd.common
from productmd.common import Header
from productmd.composeinfo import Compose

from collections import namedtuple
from itertools import chain
import six


__all__ = (
    "Image",
    "Images",
    "IMAGE_TYPE_FORMAT_MAPPING"
    "SUPPORTED_IMAGE_TYPES",
    "SUPPORTED_IMAGE_FORMATS",
    "UNIQUE_IMAGE_ATTRIBUTES",
    "UniqueImage",
)

IMAGE_TYPE_FORMAT_MAPPING = {
    'boot': ['iso'],
    'cd': ['iso'],
    'docker': ['tar.gz', 'tar.xz'],
    'dvd': ['iso'],
    # Usually non-bootable image which contains a repo with debuginfo packages.
    'dvd-debuginfo': ['iso'],
    # installer image that deploys a payload containing an ostree-based
    # distribution
    'dvd-ostree': ['iso'],
    'ec2': [],
    'kvm': [],
    'live': [],
    'liveimg-squashfs': ['liveimg.squashfs'],
    'netinst': ['iso'],
    'p2v': [],
    'qcow': ['qcow'],
    'qcow2': ['qcow2'],
    'raw': ['raw'],
    'raw-xz': ['raw.xz'],
    'rescue': [],
    'rhevm-ova': ['rhevm.ova'],
    # raw disk image named `disk.raw` stuffed into a gzipped tarball
    # format required for import by Google Compute Engine:
    # https://cloud.google.com/compute/docs/images/import-existing-image
    'tar-gz': ['tar.gz'],
    'vagrant-hyperv': ['vagrant-hyperv.box'],
    'vagrant-libvirt': ['vagrant-libvirt.box'],
    'vagrant-virtualbox': ['vagrant-virtualbox.box'],
    'vagrant-vmware-fusion': ['vagrant-vmware-fusion.box'],
    'vdi': ['vdi'],
    'vmdk': ['vmdk'],
    'vpc': ['vhd'],
    'vhd-compressed': ['vhd.gz', 'vhd.xz'],
    'vsphere-ova': ['vsphere.ova'],
}

#: supported image types
SUPPORTED_IMAGE_TYPES = list(sorted(IMAGE_TYPE_FORMAT_MAPPING.keys()))

#: supported image formats, they match with file suffix
SUPPORTED_IMAGE_FORMATS = list(sorted(set(chain(*IMAGE_TYPE_FORMAT_MAPPING.values()))))

#: combination of attributes which uniquely identifies an image across composes
UNIQUE_IMAGE_ATTRIBUTES = [
    "subvariant",
    "type",
    "format",
    "arch",
    "disc_number",
    "unified",
    "additional_variants",
]
#: a namedtuple with unique attributes, use ``identify_image`` to create an instance
UniqueImage = namedtuple('UniqueImage', UNIQUE_IMAGE_ATTRIBUTES)


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
        if self.header.version_tuple >= (1, 1):
            # disallow adding a different image with same 'unique'
            # attributes. can't do this pre-1.1 as we couldn't truly
            # identify images before subvariant
            for checkvar in self.images:
                for checkarch in self.images[checkvar]:
                    for curimg in self.images[checkvar][checkarch]:
                        if identify_image(curimg) == identify_image(image) and curimg.checksums != image.checksums:
                            raise ValueError("Image {0} shares all UNIQUE_IMAGE_ATTRIBUTES with "
                                             "image {1}! This is forbidden.".format(image, curimg))
        self.images.setdefault(variant, {}).setdefault(arch, set()).add(image)


def identify_image(image):
    """Provides a tuple of image's UNIQUE_IMAGE_ATTRIBUTES. Note:
    this is not guaranteed to be unique (and will often not be)
    for pre-1.1 metadata, as subvariant did not exist. Provided as
    a function so consumers can use it on plain image dicts read from
    the metadata or PDC.
    """
    try:
        # Image instance case
        attrs = tuple(getattr(image, attr) for attr in UNIQUE_IMAGE_ATTRIBUTES)
    except AttributeError:
        # Plain dict case
        attrs = tuple(image.get(attr, None) for attr in UNIQUE_IMAGE_ATTRIBUTES)
    ui = UniqueImage(*attrs)
    # If unified is None (which could happen in the dict case, we want default
    # value of False instead. Also convert additional_variants to a list.
    return ui._replace(
        unified=ui.unified or False, additional_variants=ui.additional_variants or []
    )


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
        self.unified = False            #: (*bool=False*) -- indicates if the ISO contains content from multiple variants
        self.additional_variants = []   #: (*[str]*) -- indicates which variants are present on the ISO

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

    def _validate_unified(self):
        self._assert_type("unified", [bool])

    def _validate_merges_variants(self):
        self._assert_type("additional_variants", [list])
        if self.additional_variants and not self.unified:
            raise ValueError("Only unified images can contain multiple variants")

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
        if self.unified:
            # Only add the `unified` field if it doesn't have the default value.
            result['unified'] = self.unified
            result["additional_variants"] = self.additional_variants
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
        self.unified = data.get('unified', False)
        self.additional_variants = data.get("additional_variants", [])
        self.validate()

    def add_checksum(self, root, checksum_type, checksum_value):
        if checksum_type in self.checksums:
            if checksum_value and checksum_value != self.checksums[checksum_type]:
                raise ValueError("Existing and added checksums do not match: %s vs %s" % (self.checksums[checksum_type], checksum_value))
            return self.checksums[checksum_type]

        self.checksums[checksum_type] = checksum_value
        return checksum_value
