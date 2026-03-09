====================
RPMs file format 2.0
====================

rpms.json files provide details about RPMs included in composes.


Changes from 1.1
=================

* ``path`` field replaced by a ``location`` object
* Location objects include ``url``, ``size``, ``checksum``, and ``local_path`` fields
* ``sigkey`` and ``category`` fields are preserved alongside the location
* URLs may be HTTPS URLs, OCI registry references, or relative paths
* Checksums use ``algorithm:hexdigest`` format (e.g., ``sha256:abc123...``)
* ``force_version`` parameter added to ``serialize()`` for version control
* ``Rpms.add()`` accepts an optional ``location`` parameter


Location Object
===============

Each RPM entry contains a ``location`` object that replaces the former ``path``
string. The ``location.local_path`` preserves the v1.x relative path for
backward-compatible filesystem layout.

See :class:`~productmd.location.Location` for details.


File Format
===========

Compose RPMs metadata is stored as a JSON serialized dictionary.
It's recommended to sort keys alphabetically and use 4 spaces for indentation
in order to read and diff rpms.json files easily.

::

    {
        "header": {
            "type": "productmd.rpms",                   # metadata type; "productmd.rpms" required
            "version": "2.0"                            # metadata version; format: $major<int>.$minor<int>
        },
        "payload": {
            "compose": {                                # see composeinfo for details
                "date": <str>,
                "id": <str>,
                "respin": <int>,
                "type": <str>
            },
            "rpms": {
                variant_uid<str>: {                     # compose variant UID
                    arch<str>: {                        # compose variant arch
                        srpm_nevra<str>: {              # N-E:V-R.A of source RPM
                            rpm_nevra<str>: {           # N-E:V-R.A of RPM file
                                "location": {           # Location object [new in 2.0]
                                    "url": <str>,       # HTTPS URL, OCI reference, or relative path
                                    "size": <int>,      # file size in bytes
                                    "checksum": <str>,  # "algorithm:hexdigest" format
                                    "local_path": <str> # relative path for v1.x filesystem layout
                                },
                                "sigkey": <str|null>,   # sigkey ID; null for unsigned RPMs
                                "category": <str>       # binary, debug, source
                            }
                        }
                    }
                }
            }
        }
    }


Examples
========

Bash and kernel RPMs in Fedora 41::

    {
        "header": {
            "type": "productmd.rpms",
            "version": "2.0"
        },
        "payload": {
            "compose": {
                "date": "20260204",
                "id": "Fedora-41-20260204.0",
                "respin": 0,
                "type": "production"
            },
            "rpms": {
                "Server": {
                    "x86_64": {
                        "bash-0:5.2.26-3.fc41.src": {
                            "bash-0:5.2.26-3.fc41.x86_64": {
                                "location": {
                                    "url": "https://cdn.fedoraproject.org/.../bash-5.2.26-3.fc41.x86_64.rpm",
                                    "size": 1849356,
                                    "checksum": "sha256:6a7b8c9d...",
                                    "local_path": "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"
                                },
                                "sigkey": "a15b79cc",
                                "category": "binary"
                            }
                        },
                        "kernel-0:6.9.5-200.fc41.src": {
                            "kernel-0:6.9.5-200.fc41.x86_64": {
                                "location": {
                                    "url": "oci://quay.io/fedora/rpms:41-server-x86_64-kernel@sha256:8c9d0e1f...",
                                    "size": 45678900,
                                    "checksum": "sha256:8c9d0e1f...",
                                    "local_path": "Server/x86_64/os/Packages/k/kernel-6.9.5-200.fc41.x86_64.rpm"
                                },
                                "sigkey": "a15b79cc",
                                "category": "binary"
                            }
                        }
                    }
                }
            }
        }
    }
