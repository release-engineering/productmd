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
from productmd.location import Location, parse_checksum
from productmd.version import VERSION_1_2, VERSION_2_0, VersionedMetadataMixin, version_to_string, OUTPUT_FORMAT_VERSION

from collections import namedtuple
from itertools import chain


__all__ = (
    "Image",
    "Images",
    "IMAGE_TYPE_FORMAT_MAPPING",
    "SUPPORTED_IMAGE_TYPES",
    "SUPPORTED_IMAGE_FORMATS",
    "UNIQUE_IMAGE_ATTRIBUTES",
    "UniqueImage",
)

IMAGE_TYPE_FORMAT_MAPPING = {
    'appx': ['appx'],
    'boot': ['iso'],
    # for all bootable container images, see https://github.com/containers/bootc
    # and https://coreos.github.io/rpm-ostree/container/
    'bootable-container': ['ociarchive'],
    'cd': ['iso'],
    'container': ['tar.xz', 'oci', 'ociarchive'],
    'docker': ['tar.gz', 'tar.xz'],
    'dvd': ['iso'],
    # Usually non-bootable image which contains a repo with debuginfo packages.
    'dvd-debuginfo': ['iso'],
    # installer image that deploys a payload containing an ostree-based
    # distribution
    'dvd-ostree': ['iso'],
    'dvd-ostree-osbuild': ['iso'],
    'ec2': [],
    # these back FEX:
    # https://fedoraproject.org/wiki/Changes/FEX
    'fex': ['erofs.xz', 'erofs.gz', 'erofs', 'squashfs.xz', 'squashfs.gz', 'squashfs'],
    'kvm': [],
    'live': [],
    'live-osbuild': ['iso'],
    'liveimg-squashfs': ['liveimg.squashfs'],
    'netinst': ['iso'],
    'ociarchive': ['ociarchive'],
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
    'vhd-compressed': ['vhd.gz', 'vhd.xz', 'vhdfixed.xz'],
    'vsphere-ova': ['vsphere.ova'],
    # https://learn.microsoft.com/en-us/windows/wsl/use-custom-distro
    'wsl2': ['tar', 'tar.gz', 'wsl'],
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


class Images(productmd.common.MetadataBase, VersionedMetadataMixin):
    def __init__(self):
        super().__init__()
        self.header = Header(self, "productmd.images")
        self.compose = Compose(self)
        self.images = {}

    def __getitem__(self, variant):
        return self.images[variant]

    def __delitem__(self, variant):
        del self.images[variant]

    def serialize(self, parser, force_version=None):
        """
        Serialize images metadata.

        :param parser: Dictionary to serialize into
        :type parser: dict
        :param force_version: Force output version (overrides output_version)
        :type force_version: tuple or None
        """
        data = parser
        output_version = self.get_output_version(force_version)

        self.header.serialize(data)

        # Ensure header version matches the output format version
        data["header"]["version"] = version_to_string(output_version)
        data["payload"] = {}
        data["payload"]["images"] = {}
        self.compose.serialize(data["payload"])

        for variant in self.images:
            for arch in self.images[variant]:
                images = data["payload"]["images"].setdefault(variant, {}).setdefault(arch, [])
                # Sort on the in-memory attribute before serializing so we
                # don't need to reach into the serialized dicts afterwards.
                for image_obj in sorted(self.images[variant][arch], key=lambda i: i.path or ""):
                    image_obj.serialize(images, force_version=output_version)
        return data

    def deserialize(self, data):
        self.header.deserialize(data)
        # Store the original file version for format detection
        file_version = self.header.version_tuple
        self.compose.deserialize(data["payload"])
        for variant in data["payload"]["images"]:
            for arch in data["payload"]["images"][variant]:
                for image in data["payload"]["images"][variant][arch]:
                    image_obj = Image(self)
                    image_obj.deserialize(image)
                    if file_version <= (1, 1):
                        self._add_1_1(data, variant, arch, image_obj)
                    else:
                        self.add(variant, arch, image_obj)
        # Preserve the file's format version so round-trips stay in the
        # same format (v1.x stays v1.x, v2.0 stays v2.0).  Files older
        # than v1.2 are upgraded to v1.2 (the last v1.x revision).
        if file_version < VERSION_1_2:
            self.output_version = VERSION_1_2
        else:
            self.output_version = file_version

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
                            raise ValueError(
                                "Image {0} shares all UNIQUE_IMAGE_ATTRIBUTES with image {1}! This is forbidden.".format(image, curimg)
                            )
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
    return ui._replace(unified=ui.unified or False, additional_variants=ui.additional_variants or [])


class Image(productmd.common.MetadataBase):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.path = None  #: (*str*) -- relative path to an image, for example: "Server/x86_64/iso/boot.iso"
        self.mtime = None  #: (*int*) -- image mtime
        self.size = None  #: (*int*) -- image size
        self.volume_id = None  #: (*str*) --
        self.type = None  #: (*str*) --
        self.format = None  #: (*str*) -- Release name, for example: "Fedora", "Red Hat Enterprise Linux"
        self.arch = None  #: (*str*) -- image architecture, for example: "x86_64", "src"
        self.disc_number = None  #: (*int*) -- Release name, for example: "Fedora", "Red Hat Enterprise Linux"
        self.disc_count = None  #: (*int*) -- Release name, for example: "Fedora", "Red Hat Enterprise Linux"
        self.checksums = {}  #: (*str*) -- Release name, for example: "Fedora", "Red Hat Enterprise Linux"
        self.implant_md5 = None  #: (*str* or *None*) -- value of implanted md5
        self.bootable = False  #: (*bool=False*) --
        self.subvariant = None  #: (*str*) -- image contents, may be same as variant or e.g. 'KDE', 'LXDE'
        self.unified = False  #: (*bool=False*) -- indicates if the ISO contains content from multiple variants
        self.additional_variants = []  #: (*[str]*) -- indicates which variants are present on the ISO
        # v2.0: Location object for distributed composes
        self._location = None  #: (:class:`productmd.location.Location` or *None*) -- v2.0 location object

    def __repr__(self):
        return "<Image:{0.path}:{0.format}:{0.arch}>".format(self)

    @property
    def location(self):
        """
        Get or create a Location object for this image (v2.0).

        For v1.2 images, this synthesizes a Location from path/size/checksums
        and caches it. For v2.0 images, this returns the stored Location.

        :return: Location object
        :rtype: :class:`productmd.location.Location`
        """
        if self._location is not None:
            return self._location

        # Synthesize a Location from v1.2 fields and cache it.
        # NOTE: url is set to the relative path (e.g. "Server/x86_64/iso/boot.iso")
        # because v1.2 data has no remote URL.  This means is_remote will
        # correctly return False, but the url field is *not* a proper URL.
        # Callers that need a real URL should set one explicitly via the
        # location setter or by assigning a new Location object.
        checksum = None
        if self.checksums:
            # Prefer sha256, fall back to first available
            if "sha256" in self.checksums:
                checksum = f"sha256:{self.checksums['sha256']}"
            else:
                algo = list(self.checksums.keys())[0]
                checksum = f"{algo}:{self.checksums[algo]}"

        self._location = Location(
            url=self.path,
            size=self.size,
            checksum=checksum,
            local_path=self.path,
        )
        return self._location

    @location.setter
    def location(self, loc):
        """
        Set the Location object for this image (v2.0).

        This also updates the v1.2 compatibility fields (path, size, checksums).
        Existing checksums are preserved; the Location's checksum is merged in.

        :param loc: Location object
        :type loc: :class:`productmd.location.Location`
        """
        self._location = loc
        if loc is not None:
            # Update v1.2 compatibility fields
            self.path = loc.local_path
            self.size = loc.size
            if loc.checksum:
                algo, digest = parse_checksum(loc.checksum)
                # Merge into existing checksums to avoid discarding
                # other algorithms (e.g. md5, sha1) that v1.x may carry.
                self.checksums[algo] = digest

    @property
    def is_remote(self):
        """
        Check if this image has a remote location (v2.0 distributed).

        :return: True if image is stored remotely
        :rtype: bool
        """
        if self._location is not None:
            return self._location.is_remote
        return False

    def _validate_path(self):
        self._assert_type("path", [str])
        self._assert_not_blank("path")

    def _validate_mtime(self):
        self._assert_type("mtime", [int])

    def _validate_size(self):
        self._assert_type("size", [int])
        self._assert_not_blank("size")

    def _validate_volume_id(self):
        self._assert_type("volume_id", [type(None), str])
        if self.volume_id is not None:
            self._assert_not_blank("volume_id")

    def _validate_type(self):
        self._assert_type("type", [str])
        self._assert_value("type", SUPPORTED_IMAGE_TYPES)

    def _validate_format(self):
        self._assert_type("format", [str])
        self._assert_value("format", SUPPORTED_IMAGE_FORMATS)

    def _validate_arch(self):
        self._assert_type("arch", [str])
        self._assert_not_blank("arch")

    def _validate_disc_number(self):
        self._assert_type("disc_number", [int])

    def _validate_disc_count(self):
        self._assert_type("disc_count", [int])

    def _validate_checksums(self):
        self._assert_type("checksums", [dict])
        self._assert_not_blank("checksums")

    def _validate_implant_md5(self):
        self._assert_type("implant_md5", [type(None), str])
        if self.implant_md5 is not None:
            self._assert_matches_re("implant_md5", [r"^[a-z0-9]{32}$"])

    def _validate_bootable(self):
        self._assert_type("bootable", [bool])

    def _validate_subvariant(self):
        self._assert_type("subvariant", [str])

    def _validate_unified(self):
        self._assert_type("unified", [bool])

    def _validate_merges_variants(self):
        self._assert_type("additional_variants", [list])
        if self.additional_variants and not self.unified:
            raise ValueError("Only unified images can contain multiple variants")

    def serialize(self, parser, force_version=None):
        """
        Serialize image to a list (appends to parser).

        :param parser: List to append serialized data to
        :type parser: list
        :param force_version: Force output version (default: use parent's version)
        :type force_version: tuple or None
        """
        data = parser
        self.validate()

        # Resolve version from parent Images instance, falling back to
        # force_version or the library default when parent is None (tests).
        if self.parent is not None:
            output_version = self.parent.get_output_version(force_version)
        elif force_version is not None:
            output_version = force_version
        else:
            output_version = OUTPUT_FORMAT_VERSION

        # v2.0 format with location object
        if output_version >= VERSION_2_0:
            result = {
                "location": self.location.serialize(),
                "mtime": self.mtime,
                "volume_id": self.volume_id,
                "type": self.type,
                "format": self.format,
                "arch": self.arch,
                "disc_number": self.disc_number,
                "disc_count": self.disc_count,
                "implant_md5": self.implant_md5,
                "bootable": self.bootable,
                "subvariant": self.subvariant,
            }
        else:
            # v1.x format with path/size/checksums
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
        """
        Deserialize image from a dictionary.

        Uses header version to determine format:
        - v2.0+: Uses Location objects
        - v1.x: Uses path/size/checksums fields

        :param data: Dictionary with image data
        :type data: dict
        """
        # Use header version for format detection (per spec section 9.1)
        if self.parent.header.version_tuple >= VERSION_2_0:
            self._deserialize_v2(data)
        else:
            self._deserialize_v1(data)
        self.validate()

    def _deserialize_v1(self, data):
        """Deserialize from v1.x format (path/size/checksums as separate fields)."""
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
        self._location = None

    def _deserialize_v2(self, data):
        """Deserialize from v2.0 format (location object)."""
        self._location = Location.from_dict(data["location"])

        # Populate v1.2 compatibility fields from location
        self.path = self._location.local_path
        self.size = self._location.size
        if self._location.checksum:
            algo, digest = parse_checksum(self._location.checksum)
            self.checksums = {algo: digest}
        else:
            self.checksums = {}

        # Other fields
        self.mtime = int(data.get("mtime", 0))
        self.volume_id = data.get("volume_id", "")
        self.type = data["type"]
        self.format = data.get("format", "iso")
        self.arch = data["arch"]
        self.disc_number = int(data.get("disc_number", 1))
        self.disc_count = int(data.get("disc_count", 1))
        self.implant_md5 = data.get("implant_md5", None)
        self.bootable = bool(data.get("bootable", False))
        self.subvariant = data.get("subvariant", "")
        self.unified = data.get('unified', False)
        self.additional_variants = data.get("additional_variants", [])

    def add_checksum(self, root, checksum_type, checksum_value):
        if checksum_type in self.checksums:
            if checksum_value and checksum_value != self.checksums[checksum_type]:
                raise ValueError("Existing and added checksums do not match: %s vs %s" % (self.checksums[checksum_type], checksum_value))
            return self.checksums[checksum_type]

        self.checksums[checksum_type] = checksum_value
        return checksum_value
