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
This module provides classes for manipulating rpms.json files.
rpms.json files provide details about RPMs included in composes.


Example::

  import productmd.compose
  compose = productmd.compose.Compose("/path/to/compose")

  # Print the entire dict that maps all variants, arches, and RPMs for this
  # compose:
  print(compose.rpms.rpms)

  # Find all the source RPMs in this compose:
  srpms = set()

  for variant in compose.rpms.rpms:
      for arch in compose.rpms.rpms[variant]:
          for srpm in compose.rpms.rpms[variant][arch]:
              srpms.add(srpm)

  print(srpms)
  # ... prints the set of SRPMs in all our variants:
  # ['ceph-2:12.2.5-25.el7cp.src',
  #  'ceph-ansible-0:3.1.0-0.1.rc9.el7cp.src',
  #  'ceph-iscsi-cli-0:2.7-1.el7cp.src',
  #  ...
  # ]
"""

import productmd.common
from productmd.common import Header
from productmd.composeinfo import Compose
from productmd.location import Location
from productmd.version import VERSION_1_2, VERSION_2_0, VersionedMetadataMixin, version_to_string


__all__ = ("Rpms",)


SUPPORTED_CATEGORIES = ["binary", "debug", "source"]


class Rpms(productmd.common.MetadataBase, VersionedMetadataMixin):
    def __init__(self):
        super().__init__()
        self.header = Header(self, "productmd.rpms")
        self.compose = Compose(self)
        self.rpms = {}

    def __getitem__(self, variant):
        return self.rpms[variant]

    def __delitem__(self, variant):
        del self.rpms[variant]

    def _check_nevra(self, nevra):
        if ":" not in nevra:
            raise ValueError("Missing epoch in N-E:V-R.A: %s" % nevra)

        try:
            nevra_dict = productmd.common.parse_nvra(nevra)
        except ValueError:
            raise ValueError("Invalid N-E:V-R.A: %s" % nevra)

        nevra_dict["epoch"] = nevra_dict["epoch"] or 0
        nevra = "%(name)s-%(epoch)s:%(version)s-%(release)s.%(arch)s" % nevra_dict
        return nevra, nevra_dict

    def serialize(self, parser, force_version=None):
        """
        Serialize RPM metadata.

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
        data["payload"]["rpms"] = {}
        self.compose.serialize(data["payload"])

        if output_version >= VERSION_2_0:
            self._serialize_v2(data)
        else:
            self._serialize_v1(data)

        return data

    def _serialize_v1(self, data):
        """Serialize RPM entries in v1.x format (path/sigkey/category)."""
        v1_rpms = {}
        for variant in self.rpms:
            v1_rpms[variant] = {}
            for arch in self.rpms[variant]:
                v1_rpms[variant][arch] = {}
                for srpm_nevra in self.rpms[variant][arch]:
                    v1_rpms[variant][arch][srpm_nevra] = {}
                    for rpm_nevra, rpm_data in self.rpms[variant][arch][srpm_nevra].items():
                        # Strip internal _location key; output only v1.x fields
                        v1_rpms[variant][arch][srpm_nevra][rpm_nevra] = {
                            "sigkey": rpm_data.get("sigkey"),
                            "path": rpm_data.get("path", ""),
                            "category": rpm_data.get("category"),
                        }
        data["payload"]["rpms"] = v1_rpms

    def _serialize_v2(self, data):
        """Serialize RPM entries in v2.0 format (path replaced by location)."""
        v2_rpms = {}
        for variant in self.rpms:
            v2_rpms[variant] = {}
            for arch in self.rpms[variant]:
                v2_rpms[variant][arch] = {}
                for srpm_nevra in self.rpms[variant][arch]:
                    v2_rpms[variant][arch][srpm_nevra] = {}
                    for rpm_nevra, rpm_data in self.rpms[variant][arch][srpm_nevra].items():
                        v2_entry = {}

                        # Build location from path
                        path = rpm_data.get("path", "")
                        loc = rpm_data.get("_location")
                        if loc is not None:
                            v2_entry["location"] = loc.serialize()
                        else:
                            # Fallback for v1.x data without an explicit Location:
                            # size and checksum will be None since v1.x RPM entries
                            # don't carry these fields. A localization tool or
                            # compute_checksum pass would populate them.
                            v2_entry["location"] = Location(
                                url=path,
                                size=rpm_data.get("size"),
                                checksum=rpm_data.get("checksum"),
                                local_path=path,
                            ).serialize()

                        # Carry over sigkey and category
                        v2_entry["sigkey"] = rpm_data.get("sigkey")
                        v2_entry["category"] = rpm_data.get("category")

                        v2_rpms[variant][arch][srpm_nevra][rpm_nevra] = v2_entry

        data["payload"]["rpms"] = v2_rpms

    def deserialize(self, data):
        self.header.deserialize(data)
        file_version = self.header.version_tuple

        if file_version <= (0, 3):
            self._deserialize_0_3(data)
        elif file_version >= VERSION_2_0:
            self._deserialize_v2(data)
        else:
            self._deserialize_v1(data)
        self.validate()

        # Preserve the file's format version so round-trips stay in the
        # same format. v0.3 files are upgraded to v1.2 since they undergo
        # structural conversion in _deserialize_0_3.
        if file_version <= (0, 3):
            self.output_version = VERSION_1_2
        else:
            self.output_version = file_version

    def _deserialize_0_3(self, data):
        self.compose.deserialize(data["payload"])
        payload = data["payload"]["manifest"]
        self.rpms = {}
        for variant in payload:
            for arch in payload[variant]:
                if arch == "src":
                    continue
                for srpm_nevra, rpms in payload[variant][arch].items():
                    srpm_data = payload[variant].get("src", {}).get(srpm_nevra, None)
                    for rpm_nevra, rpm_data in rpms.items():
                        category = rpm_data["type"]
                        if category == "package":
                            category = "binary"
                        self.add(variant, arch, rpm_nevra, rpm_data["path"], rpm_data["sigkey"], category, srpm_nevra)
                        if srpm_data is not None:
                            self.add(variant, arch, srpm_nevra, srpm_data["path"], srpm_data["sigkey"], "source")

    def _deserialize_v1(self, data):
        """Deserialize from v1.x format (path/sigkey/category as direct fields)."""
        self.compose.deserialize(data["payload"])
        # NOTE: directly references the input dict — mutations to self.rpms
        # (e.g. via add()) will also mutate the input data. This is
        # pre-existing behavior preserved for backward compatibility.
        self.rpms = data["payload"]["rpms"]

    def _deserialize_v2(self, data):
        """Deserialize from v2.0 format (location object replaces path)."""
        self.compose.deserialize(data["payload"])
        self.rpms = {}
        payload_rpms = data["payload"]["rpms"]

        for variant in payload_rpms:
            self.rpms[variant] = {}
            for arch in payload_rpms[variant]:
                self.rpms[variant][arch] = {}
                for srpm_nevra in payload_rpms[variant][arch]:
                    self.rpms[variant][arch][srpm_nevra] = {}
                    for rpm_nevra, rpm_data in payload_rpms[variant][arch][srpm_nevra].items():
                        loc = Location.from_dict(rpm_data["location"])

                        # Store in v1.x-compatible internal format
                        entry = {
                            "sigkey": rpm_data.get("sigkey"),
                            "path": loc.local_path,
                            "category": rpm_data.get("category"),
                        }

                        # Preserve full location for round-trip fidelity
                        entry["_location"] = loc

                        self.rpms[variant][arch][srpm_nevra][rpm_nevra] = entry

    def add(self, variant, arch, nevra, path, sigkey, category, srpm_nevra=None, location=None):
        """
        Map RPM to to variant and arch.

        :param variant: compose variant UID
        :type  variant: str
        :param arch:    compose architecture
        :type  arch:    str
        :param nevra:   name-epoch:version-release.arch
        :type  nevra:   str
        :param path:    relative path to the RPM file
        :type  path:    str
        :param sigkey:  sigkey hash
        :type  sigkey:  str or None
        :param category:    RPM category, one of binary, debug, source
        :type  category:    str
        :param srpm_nevra:  name-epoch:version-release.arch of RPM's SRPM
        :type  srpm_nevra:  str
        :param location:    Location object for v2.0 distributed composes.
            When provided, the Location is stored alongside v1.x fields
            and used during v2.0 serialization. The *path* parameter is
            still required for v1.x compatibility; if *location* is given
            and *path* is not explicitly set, *path* defaults to
            ``location.local_path``.
        :type  location:    :class:`~productmd.location.Location` or None
        """

        # When location is provided without an explicit path, derive path
        # from location.local_path for v1.x backward compatibility.
        if location is not None and path is None:
            path = location.local_path

        if path is None:
            raise ValueError("Either 'path' or 'location' must be provided")

        if location is not None and not isinstance(location, Location):
            raise TypeError(f"'location' must be a Location instance, got: {type(location)}")

        if arch not in productmd.common.RPM_ARCHES:
            raise ValueError("Arch not found in RPM_ARCHES: %s" % arch)

        if arch in ["src", "nosrc"]:
            raise ValueError("Source arch is not allowed. Map source files under binary arches.")

        if category not in SUPPORTED_CATEGORIES:
            raise ValueError("Invalid category value: %s" % category)

        if path.startswith("/"):
            raise ValueError("Relative path expected: %s" % path)

        nevra, nevra_dict = self._check_nevra(nevra)

        if category == "source" and srpm_nevra is not None:
            raise ValueError("Expected blank srpm_nevra for source package: %s" % nevra)

        if category != "source" and srpm_nevra is None:
            raise ValueError("Missing srpm_nevra for package: %s" % nevra)

        if (category == "source") != (nevra_dict["arch"] in ("src", "nosrc")):
            raise ValueError("Invalid category/arch combination: %s/%s" % (category, nevra))

        if sigkey is not None:
            sigkey = sigkey.lower()

        if srpm_nevra:
            srpm_nevra, _ = self._check_nevra(srpm_nevra)
        else:
            srpm_nevra = nevra

        arches = self.rpms.setdefault(variant, {})
        srpms = arches.setdefault(arch, {})
        rpms = srpms.setdefault(srpm_nevra, {})
        entry = {"sigkey": sigkey, "path": path, "category": category}
        if location is not None:
            entry["_location"] = location
        rpms[nevra] = entry
