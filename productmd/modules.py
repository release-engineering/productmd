# -*- coding: utf-8 -*-

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
import six

import productmd.common
from productmd.common import Header, RPM_ARCHES
from productmd.composeinfo import Compose
from productmd.rpms import SUPPORTED_CATEGORIES

__all__ = (
    "Modules",
)


class Modules(productmd.common.MetadataBase):
    def __init__(self):
        super(Modules, self).__init__()
        self.header = Header(self, "productmd.modules")
        self.compose = Compose(self)
        self.modules = {}

    def __getitem__(self, variant):
        return self.modules[variant]

    def __delitem__(self, variant):
        del self.modules[variant]

    @staticmethod
    def parse_uid(uid):
        if not isinstance(uid, six.string_types):
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
        if not isinstance(uid, six.string_types):
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

    def serialize(self, parser):
        self.validate()
        data = parser
        self.header.serialize(data)
        data["payload"] = {}
        self.compose.serialize(data["payload"])
        data["payload"]["modules"] = self.modules
        return data

    def deserialize(self, data):
        self.header.deserialize(data)
        self.compose.deserialize(data["payload"])
        self.modules = data["payload"]["modules"]
        self.validate()

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
