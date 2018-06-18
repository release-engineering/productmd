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


__all__ = (
    "Rpms",
)


SUPPORTED_CATEGORIES = ["binary", "debug", "source"]


class Rpms(productmd.common.MetadataBase):
    def __init__(self):
        super(Rpms, self).__init__()
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

    def serialize(self, parser):
        data = parser
        self.header.serialize(data)
        data["payload"] = {}
        data["payload"]["rpms"] = {}
        self.compose.serialize(data["payload"])
        data["payload"]["rpms"] = self.rpms
        return data

    def deserialize(self, data):
        self.header.deserialize(data)
        if self.header.version_tuple <= (0, 3):
            self.deserialize_0_3(data)
        else:
            self.deserialize_1_0(data)
        self.validate()

        self.header.set_current_version()

    def deserialize_0_3(self, data):
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

    def deserialize_1_0(self, data):
        self.compose.deserialize(data["payload"])
        self.rpms = data["payload"]["rpms"]

    def add(self, variant, arch, nevra, path, sigkey, category, srpm_nevra=None):
        """
        Map RPM to to variant and arch.

        :param variant: compose variant UID
        :type  variant: str
        :param arch:    compose architecture
        :type  arch:    str
        :param nevra:   name-epoch:version-release.arch
        :type  nevra:   str
        :param sigkey:  sigkey hash
        :type  sigkey:  str or None
        :param category:    RPM category, one of binary, debug, source
        :type  category:    str
        :param srpm_nevra:  name-epoch:version-release.arch of RPM's SRPM
        :type  srpm_nevra:  str
        """

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
        rpms[nevra] = {"sigkey": sigkey, "path": path, "category": category}
