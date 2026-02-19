# Copyright (C) 2017  Red Hat, Inc.
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

import re

import productmd.common
from productmd.common import Header, RPM_ARCHES
from productmd.composeinfo import Compose
from productmd.location import Location
from productmd.rpms import SUPPORTED_CATEGORIES
from productmd.version import VERSION_2_0, VersionedMetadataMixin, version_to_string

__all__ = ("Modules",)


class Modules(productmd.common.MetadataBase, VersionedMetadataMixin):
    def __init__(self):
        super().__init__()
        self.header = Header(self, "productmd.modules")
        self.compose = Compose(self)
        self.modules = {}

    def __getitem__(self, variant):
        return self.modules[variant]

    def __delitem__(self, variant):
        del self.modules[variant]

    @staticmethod
    def parse_uid(uid):
        if not isinstance(uid, str):
            raise ValueError("Uid has to be string: %s" % uid)

        # pattern to parse uid MODULE_NAME:STREAM[:VERSION[:CONTEXT]]
        UID_RE = re.compile(r"^(.*/)?(?P<module_name>[^:]+):(?P<stream>[^:]+)(:(?P<version>[^:]+))?(:(?P<context>[^:]+))?$")
        matched = UID_RE.match(uid)
        if matched:
            uid_dict = matched.groupdict()
        else:
            raise ValueError("Invalid uid: %s" % uid)

        if uid_dict["version"] is None:
            uid_dict["version"] = ""
        if uid_dict["context"] is None:
            uid_dict["context"] = ""

        return uid_dict

    def _check_uid(self, uid):
        if not isinstance(uid, str):
            raise ValueError("Uid has to be string: %s" % uid)
        if ":" not in uid:
            raise ValueError("Missing stream in uid: %s" % uid)

        try:
            uid_dict = self.parse_uid(uid)
        except ValueError:
            raise ValueError("Invalid uid format: %s" % uid)

        uid = "%(module_name)s:%(stream)s" % uid_dict
        uid += ":%s" % uid_dict['version'] if uid_dict['version'] else ""
        uid += ":%s" % uid_dict['context'] if uid_dict['context'] else ""
        return uid, uid_dict

    def serialize(self, parser, force_version=None):
        """
        Serialize module metadata.

        :param parser: Dictionary to serialize into
        :type parser: dict
        :param force_version: Force output version (overrides output_version)
        :type force_version: tuple or None
        """
        self.validate()
        data = parser
        output_version = self.get_output_version(force_version)

        self.header.serialize(data)

        # Ensure header version matches the output format version
        data["header"]["version"] = version_to_string(output_version)
        data["payload"] = {}
        self.compose.serialize(data["payload"])

        if output_version >= VERSION_2_0:
            self._serialize_v2(data)
        else:
            self._serialize_v1(data)

        return data

    @staticmethod
    def _get_modulemd_path(entry):
        """Extract the first modulemd path from an entry.

        Handles both v1.0 format (modulemd_path is a string) and
        v1.1+ format (modulemd_path is a dict mapping category to path).

        :param entry: Module entry dict
        :type entry: dict
        :return: First path string, or empty string if not found
        :rtype: str
        """
        modulemd_path = entry.get("modulemd_path", {})
        if isinstance(modulemd_path, str):
            return modulemd_path
        if isinstance(modulemd_path, dict) and modulemd_path:
            return next(iter(modulemd_path.values()))
        return ""

    def _serialize_v1(self, data):
        """Serialize module entries in v1.x format (metadata/modulemd_path)."""
        v1_modules = {}
        for variant in self.modules:
            v1_modules[variant] = {}
            for arch in self.modules[variant]:
                v1_modules[variant][arch] = {}
                for uid, entry in self.modules[variant][arch].items():
                    # Strip internal _location key; output only v1.x fields
                    v1_entry = {}
                    v1_entry["metadata"] = dict(entry.get("metadata", {}))
                    modulemd_path = entry.get("modulemd_path", {})
                    if isinstance(modulemd_path, dict):
                        v1_entry["modulemd_path"] = dict(modulemd_path)
                    else:
                        v1_entry["modulemd_path"] = modulemd_path
                    v1_entry["rpms"] = list(entry.get("rpms", []))
                    v1_modules[variant][arch][uid] = v1_entry
        data["payload"]["modules"] = v1_modules

    def _serialize_v2(self, data):
        """Serialize module entries in v2.0 format (flattened, location object)."""
        v2_modules = {}
        for variant in self.modules:
            v2_modules[variant] = {}
            for arch in self.modules[variant]:
                v2_modules[variant][arch] = {}
                for uid, entry in self.modules[variant][arch].items():
                    metadata = entry.get("metadata", {})
                    v2_entry = {
                        "name": metadata.get("name", ""),
                        "stream": metadata.get("stream", ""),
                        "version": metadata.get("version", ""),
                        "context": metadata.get("context", ""),
                        "arch": arch,
                    }

                    # Build location from modulemd_path or existing _location
                    loc = entry.get("_location")
                    if loc is not None:
                        v2_entry["location"] = loc.serialize()
                    else:
                        path = self._get_modulemd_path(entry)
                        v2_entry["location"] = Location(
                            url=path,
                            local_path=path,
                        ).serialize()

                    v2_entry["rpms"] = list(entry.get("rpms", []))
                    v2_modules[variant][arch][uid] = v2_entry
        data["payload"]["modules"] = v2_modules

    def deserialize(self, data):
        self.header.deserialize(data)
        file_version = self.header.version_tuple

        if file_version >= VERSION_2_0:
            self._deserialize_v2(data)
        else:
            self._deserialize_v1(data)
        self.validate()

        # Preserve the file's format version so round-trips stay in the
        # same format.
        self.output_version = file_version

    def _deserialize_v1(self, data):
        """Deserialize from v1.x format (metadata/modulemd_path as direct fields)."""
        self.compose.deserialize(data["payload"])
        # NOTE: directly references the input dict — mutations to self.modules
        # (e.g. via add()) will also mutate the input data. This is
        # pre-existing behavior preserved for backward compatibility.
        self.modules = data["payload"]["modules"]

    def _deserialize_v2(self, data):
        """Deserialize from v2.0 format (flattened fields, location object)."""
        self.compose.deserialize(data["payload"])
        self.modules = {}
        payload_modules = data["payload"]["modules"]

        for variant in payload_modules:
            self.modules[variant] = {}
            for arch in payload_modules[variant]:
                self.modules[variant][arch] = {}
                for uid, v2_entry in payload_modules[variant][arch].items():
                    loc = Location.from_dict(v2_entry["location"])

                    # Reconstruct v1.x-compatible internal format
                    name = v2_entry.get("name", "")
                    stream = v2_entry.get("stream", "")
                    version = v2_entry.get("version", "")
                    context = v2_entry.get("context", "")

                    entry = {
                        "metadata": {
                            "uid": uid,
                            "name": name,
                            "stream": stream,
                            "version": version,
                            "context": context,
                            "koji_tag": "",
                        },
                        # v2.0 has a single location replacing the category→path
                        # dict. Only "binary" is reconstructed; other categories
                        # (if they existed in the original v1.x data) are lost.
                        "modulemd_path": {"binary": loc.local_path},
                        "rpms": list(v2_entry.get("rpms", [])),
                    }

                    # Preserve full location for round-trip fidelity
                    entry["_location"] = loc

                    self.modules[variant][arch][uid] = entry

    def add(self, variant, arch, uid, koji_tag, modulemd_path, category, rpms):
        if not variant:
            raise ValueError("Non-empty variant is expected")

        if arch not in RPM_ARCHES:
            raise ValueError("Arch not found in RPM_ARCHES: %s" % arch)

        if category not in SUPPORTED_CATEGORIES:
            raise ValueError("Invalid category value: %s" % category)

        uid, uid_dict = self._check_uid(uid)
        name = uid_dict["module_name"]
        stream = uid_dict["stream"]
        version = uid_dict["version"]
        context = uid_dict["context"]

        if modulemd_path.startswith("/"):
            raise ValueError("Relative path expected: %s" % modulemd_path)

        if not koji_tag:
            raise ValueError("Non-empty 'koji_tag' is expected")

        for param_name, param in {"variant": variant, "koji_tag": koji_tag, "modulemd_path": modulemd_path}.items():
            if not param:
                raise ValueError("Non-empty '%s' is expected" % param_name)

        if not isinstance(rpms, (list, tuple)):
            raise ValueError("Wrong type of 'rpms'")

        arches = self.modules.setdefault(variant, {})
        uids = arches.setdefault(arch, {})
        metadata = uids.setdefault(uid, {})
        metadata["metadata"] = {
            "uid": uid,
            "name": name,
            "stream": stream,
            "version": version,
            "context": context,
            "koji_tag": koji_tag,
        }
        metadata.setdefault("modulemd_path", {})[category] = modulemd_path
        metadata.setdefault("rpms", []).extend(list(rpms))
