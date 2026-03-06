========================
Modules file format 2.0
========================

modules.json files provide details about modules included in composes.


Changes from 1.x
=================

* ``metadata`` wrapper dict is eliminated; fields are flattened to top level
* ``koji_tag`` field removed from output
* ``uid`` field removed from output (reconstructable from the dict key)
* ``arch`` field added to each module entry
* ``modulemd_path`` (category-to-path dict) replaced by a single ``location`` object
* Location objects include ``url``, ``size``, ``checksum``, and ``local_path`` fields
* URLs may be HTTPS URLs, OCI registry references, or relative paths
* Checksums use ``algorithm:hexdigest`` format (e.g., ``sha256:abc123...``)
* ``force_version`` parameter added to ``serialize()`` for version control


Location Object
===============

Each module entry contains a ``location`` object that replaces the former
``modulemd_path`` dict. The ``location.local_path`` preserves the v1.x relative
path for backward-compatible filesystem layout.

See :class:`~productmd.location.Location` for details.


File Format
===========

Compose modules metadata is stored as a JSON serialized dictionary.
It's recommended to sort keys alphabetically and use 4 spaces for indentation
in order to read and diff modules.json files easily.

::

    {
        "header": {
            "type": "productmd.modules",                # metadata type; "productmd.modules" required
            "version": "2.0"                            # metadata version; format: $major<int>.$minor<int>
        },
        "payload": {
            "compose": {                                # see composeinfo for details
                "date": <str>,
                "id": <str>,
                "respin": <int>,
                "type": <str>
            },
            "modules": {
                variant_uid<str>: {                     # compose variant UID
                    arch<str>: {                        # compose variant arch
                        module_uid<str>: {              # NAME:STREAM:VERSION:CONTEXT
                            "name": <str>,              # module name [flattened in 2.0]
                            "stream": <str>,            # module stream [flattened in 2.0]
                            "version": <str>,           # module version [flattened in 2.0]
                            "context": <str>,           # module context [flattened in 2.0]
                            "arch": <str>,              # architecture [new in 2.0]
                            "location": {               # Location object [new in 2.0]
                                "url": <str>,           # HTTPS URL, OCI reference, or relative path
                                "size": <int>,          # size in bytes
                                "checksum": <str>,      # "algorithm:hexdigest" format
                                "local_path": <str>     # relative path for v1.x filesystem layout
                            },
                            "rpms": [<str>]             # list of RPM filenames in this module
                        }
                    }
                }
            }
        }
    }


Comparison with v1.x Format
============================

v1.x module entry::

    {
        "metadata": {
            "uid": "nodejs:20:4120250101112233:f41",
            "name": "nodejs",
            "stream": "20",
            "version": "4120250101112233",
            "context": "f41",
            "koji_tag": "module-66c333b434067fb3a"
        },
        "modulemd_path": {
            "binary": "Server/x86_64/os/repodata/modules.yaml.gz"
        },
        "rpms": ["nodejs-1:20.10.0-1.module_f41+12345+abcdef12.x86_64.rpm"]
    }

v2.0 module entry::

    {
        "name": "nodejs",
        "stream": "20",
        "version": "4120250101112233",
        "context": "f41",
        "arch": "x86_64",
        "location": {
            "url": "oci://quay.io/fedora/modules:nodejs-20-x86_64@sha256:abcdef12...",
            "size": 45678900,
            "checksum": "sha256:abcdef12...",
            "local_path": "Server/x86_64/os/Packages"
        },
        "rpms": ["nodejs-1:20.10.0-1.module_f41+12345+abcdef12.x86_64.rpm"]
    }


Examples
========

Fedora 41 modules with OCI and HTTPS URLs::

    {
        "header": {
            "type": "productmd.modules",
            "version": "2.0"
        },
        "payload": {
            "compose": {
                "date": "20260204",
                "id": "Fedora-41-20260204.0",
                "respin": 0,
                "type": "production"
            },
            "modules": {
                "Server": {
                    "x86_64": {
                        "nodejs:20:4120250101112233:f41": {
                            "name": "nodejs",
                            "stream": "20",
                            "version": "4120250101112233",
                            "context": "f41",
                            "arch": "x86_64",
                            "location": {
                                "url": "oci://quay.io/fedora/modules:nodejs-20-x86_64@sha256:abcdef12...",
                                "size": 45678900,
                                "checksum": "sha256:abcdef12...",
                                "local_path": "Server/x86_64/os/Packages"
                            },
                            "rpms": [
                                "nodejs-1:20.10.0-1.module_f41+12345+abcdef12.x86_64.rpm",
                                "npm-1:10.2.3-1.module_f41+12345+abcdef12.x86_64.rpm"
                            ]
                        },
                        "postgresql:16:4120250101223344:f41": {
                            "name": "postgresql",
                            "stream": "16",
                            "version": "4120250101223344",
                            "context": "f41",
                            "arch": "x86_64",
                            "location": {
                                "url": "https://cdn.fedoraproject.org/.../Server/x86_64/os/Packages/",
                                "size": 0,
                                "checksum": "sha256:fedcba09...",
                                "local_path": "Server/x86_64/os/Packages"
                            },
                            "rpms": [
                                "postgresql-16.1-2.module_f41+23456+bcdef123.x86_64.rpm",
                                "postgresql-server-16.1-2.module_f41+23456+bcdef123.x86_64.rpm"
                            ]
                        }
                    }
                }
            }
        }
    }
