# Copyright (C) 2019  Red Hat, Inc.
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
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, see <https://gnu.org/licenses/>.

import json
import os

import productmd.common
from productmd.common import Header, RPM_ARCHES
from productmd.composeinfo import Compose
from productmd.location import Location, parse_checksum
from productmd.version import VERSION_2_0, VersionedMetadataMixin, version_to_string

__all__ = ("ExtraFiles",)


class ExtraFiles(productmd.common.MetadataBase, VersionedMetadataMixin):
    def __init__(self):
        super().__init__()
        self.header = Header(self, "productmd.extra_files")
        self.compose = Compose(self)
        self.extra_files = {}

    def __getitem__(self, variant):
        return self.extra_files[variant]

    def __delitem__(self, variant):
        del self.extra_files[variant]

    def serialize(self, parser, force_version=None):
        """
        Serialize extra files metadata.

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

    def _serialize_v1(self, data):
        """Serialize extra file entries in v1.x format (file/size/checksums)."""
        v1_extra = {}
        for variant in self.extra_files:
            v1_extra[variant] = {}
            for arch in self.extra_files[variant]:
                v1_extra[variant][arch] = []
                for entry in self.extra_files[variant][arch]:
                    # Strip internal _location key; output only v1.x fields
                    v1_extra[variant][arch].append(
                        {
                            "file": entry["file"],
                            "size": entry["size"],
                            "checksums": entry["checksums"],
                        }
                    )
        data["payload"]["extra_files"] = v1_extra

    def _serialize_v2(self, data):
        """Serialize extra file entries in v2.0 format (file + location)."""
        v2_extra = {}
        for variant in self.extra_files:
            v2_extra[variant] = {}
            for arch in self.extra_files[variant]:
                v2_extra[variant][arch] = []
                for entry in self.extra_files[variant][arch]:
                    loc = entry.get("_location")
                    if loc is not None:
                        loc_dict = loc.serialize()
                    else:
                        # Synthesize Location from v1.x fields
                        checksum = None
                        checksums = entry.get("checksums", {})
                        if checksums:
                            if "sha256" in checksums:
                                checksum = f"sha256:{checksums['sha256']}"
                            else:
                                algo = list(checksums.keys())[0]
                                checksum = f"{algo}:{checksums[algo]}"

                        loc_dict = Location(
                            url=entry["file"],
                            size=entry.get("size"),
                            checksum=checksum,
                            local_path=entry["file"],
                        ).serialize()

                    v2_extra[variant][arch].append(
                        {
                            "file": os.path.basename(entry["file"]),
                            "location": loc_dict,
                        }
                    )
        data["payload"]["extra_files"] = v2_extra

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
        """Deserialize from v1.x format (file/size/checksums as direct fields)."""
        self.compose.deserialize(data["payload"])
        # NOTE: directly references the input dict — mutations to self.extra_files
        # (e.g. via add()) will also mutate the input data. This is
        # pre-existing behavior preserved for backward compatibility.
        self.extra_files = data["payload"]["extra_files"]

    def _deserialize_v2(self, data):
        """Deserialize from v2.0 format (file + location object)."""
        self.compose.deserialize(data["payload"])
        self.extra_files = {}
        payload_extra = data["payload"]["extra_files"]

        for variant in payload_extra:
            self.extra_files[variant] = {}
            for arch in payload_extra[variant]:
                self.extra_files[variant][arch] = []
                for item in payload_extra[variant][arch]:
                    loc = Location.from_dict(item["location"])

                    # Build checksums dict from location checksum string
                    checksums = {}
                    if loc.checksum:
                        algo, digest = parse_checksum(loc.checksum)
                        checksums = {algo: digest}

                    # Store in v1.x-compatible internal format
                    entry = {
                        "file": loc.local_path,
                        "size": loc.size,
                        "checksums": checksums,
                    }

                    # Preserve full location for round-trip fidelity
                    entry["_location"] = loc

                    self.extra_files[variant][arch].append(entry)

    def add(self, variant, arch, path, size, checksums):
        if not variant:
            raise ValueError("Non-empty variant is expected")

        if arch not in RPM_ARCHES:
            raise ValueError("Arch not found in RPM_ARCHES: %s" % arch)

        if not path:
            raise ValueError("Path can not be empty.")

        if path.startswith("/"):
            raise ValueError("Relative path expected: %s" % path)

        if not isinstance(checksums, dict):
            raise TypeError("Checksums must be a dict.")

        metadata = self.extra_files.setdefault(variant, {}).setdefault(arch, [])
        metadata.append({"file": path, "size": size, "checksums": checksums})

    def dump_for_tree(self, output, variant, arch, basepath):
        """Dump the serialized metadata for given tree. The basepath is
        stripped from all paths.
        """
        metadata = {"header": {"version": "1.0"}, "data": []}
        for item in self.extra_files[variant][arch]:
            metadata["data"].append(
                {
                    "file": _relative_to(item["file"], basepath),
                    "size": item["size"],
                    "checksums": item["checksums"],
                }
            )

        json.dump(metadata, output, sort_keys=True, indent=4, separators=(",", ": "))


def _relative_to(path, root):
    root = root.rstrip("/") + "/"
    if path.startswith(root):
        return path[len(root) :]
    return path
