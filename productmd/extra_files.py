# -*- coding: utf-8 -*-

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

import productmd.common
from productmd.common import Header, RPM_ARCHES
from productmd.composeinfo import Compose

__all__ = (
    "ExtraFiles",
)


class ExtraFiles(productmd.common.MetadataBase):
    def __init__(self):
        super(ExtraFiles, self).__init__()
        self.header = Header(self, "productmd.extra_files")
        self.compose = Compose(self)
        self.extra_files = {}

    def __getitem__(self, variant):
        return self.extra_files[variant]

    def __delitem__(self, variant):
        del self.extra_files[variant]

    def serialize(self, parser):
        self.validate()
        data = parser
        self.header.serialize(data)
        data["payload"] = {}
        self.compose.serialize(data["payload"])
        data["payload"]["extra_files"] = self.extra_files
        return data

    def deserialize(self, data):
        self.header.deserialize(data)
        self.compose.deserialize(data["payload"])
        self.extra_files = data["payload"]["extra_files"]
        self.validate()

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
        return path[len(root):]
    return path
