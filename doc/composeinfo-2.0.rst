===========================
Composeinfo file format 2.0
===========================

composeinfo.json files provide details about composes which includes
product information, variants, architectures and paths.


Changes from 1.1
=================

* Variant paths are now :class:`~productmd.location.Location` objects instead of plain strings
* Location objects include ``url``, ``size``, ``checksum``, and ``local_path`` fields
* URLs may be HTTPS URLs, OCI registry references, or relative paths
* Checksums use ``algorithm:hexdigest`` format (e.g., ``sha256:abc123...``)
* ``force_version`` parameter added to ``serialize()`` for version control


Location Object
===============

All variant paths (``os_tree``, ``packages``, ``source_tree``, ``source_packages``,
``debug_tree``, ``debug_packages``, ``repository``, ``source_repository``,
``debug_repository``, ``identity``, ``isos``, ``jigdos``) are stored as Location objects
in v2.0 format, instead of plain relative path strings.

See :class:`~productmd.location.Location` for details.


File Format
===========
Composeinfo is stored as a JSON serialized dictionary.
It's recommended to sort keys alphabetically and use 4 spaces for indentation
in order to read and diff composeinfo.json files easily.


::

    {
        "header": {
            "type": "productmd.composeinfo",            # metadata type; "productmd.composeinfo" required
            "version": "2.0"                            # metadata version; format: $major<int>.$minor<int>
        },
        "payload": {
            "compose": {
                "id": <str>,
                "date": <str>,
                "respin": <int>,
                "type": <str>,
                "label": <str|unset>,
                "final": <bool=false>
            },
            "release": {
                "name": <str>,
                "version": <str>,
                "short": <str>,
                "type": <str>,
                "is_layered": <bool=false>,
            },
            "base_product": {                           # optional; present only for layered products
                "name": <str>,
                "version": <str>,
                "short": <str>,
                "type": <str>,
            },
            "variants": {
                variant_uid<str>: {
                    "id": <str>,
                    "uid": <str>,
                    "name": <str>,
                    "type": <str>,
                    "arches": [<str>],
                    "paths": {
                        path_category<str>: {           # os_tree, packages, source_tree, etc.
                            arch<str>: {                # Location object [changed in 2.0]
                                "url": <str>,           # HTTPS URL, OCI reference, or relative path
                                "size": <int>,          # size in bytes
                                "checksum": <str>,      # "algorithm:hexdigest" format
                                "local_path": <str>,    # relative path for v1.x filesystem layout
                            },
                        },
                    },
                },
            },
        },
    }


Examples
========

Fedora 41 compose with HTTPS URLs::

    {
        "header": {
            "type": "productmd.composeinfo",
            "version": "2.0"
        },
        "payload": {
            "compose": {
                "date": "20260204",
                "id": "Fedora-41-20260204.0",
                "respin": 0,
                "type": "production",
                "label": "GA"
            },
            "release": {
                "name": "Fedora",
                "short": "Fedora",
                "version": "41",
                "is_layered": false,
                "type": "ga"
            },
            "variants": {
                "Server": {
                    "id": "Server",
                    "uid": "Server",
                    "name": "Fedora Server",
                    "type": "variant",
                    "arches": ["x86_64", "aarch64"],
                    "paths": {
                        "os_tree": {
                            "x86_64": {
                                "url": "https://cdn.fedoraproject.org/.../Server/x86_64/os/",
                                "size": 2847,
                                "checksum": "sha256:a1b2c3d4...",
                                "local_path": "Server/x86_64/os"
                            }
                        },
                        "packages": {
                            "x86_64": {
                                "url": "https://cdn.fedoraproject.org/.../Server/x86_64/os/Packages/",
                                "size": 0,
                                "checksum": "sha256:c3d4e5f6...",
                                "local_path": "Server/x86_64/os/Packages"
                            }
                        }
                    }
                }
            }
        }
    }
