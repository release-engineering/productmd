============================
Extra files file format 2.0
============================

extra_files.json files provide details about extra (non-RPM, non-image) files
included in composes, such as license files, GPG keys, and EULAs.


Changes from 1.x
=================

* ``size`` and ``checksums`` fields replaced by a ``location`` object
* ``file`` field now contains only the filename (basename), not the full relative path
* Location objects include ``url``, ``size``, ``checksum``, and ``local_path`` fields
* URLs may be HTTPS URLs, OCI registry references, or relative paths
* Checksums use ``algorithm:hexdigest`` format (e.g., ``sha256:abc123...``)
* ``force_version`` parameter added to ``serialize()`` for version control


Location Object
===============

Each extra file entry contains a ``location`` object instead of separate ``size``
and ``checksums`` fields. The ``location.local_path`` preserves the v1.x full
relative path, while the ``file`` field is simplified to just the basename.

See :class:`~productmd.location.Location` for details.


File Format
===========

Compose extra files metadata is stored as a JSON serialized dictionary.
It's recommended to sort keys alphabetically and use 4 spaces for indentation
in order to read and diff extra_files.json files easily.

::

    {
        "header": {
            "type": "productmd.extra_files",            # metadata type; "productmd.extra_files" required
            "version": "2.0"                            # metadata version; format: $major<int>.$minor<int>
        },
        "payload": {
            "compose": {                                # see composeinfo for details
                "date": <str>,
                "id": <str>,
                "respin": <int>,
                "type": <str>
            },
            "extra_files": {
                variant_uid<str>: {                     # compose variant UID
                    arch<str>: [                        # compose variant arch
                        {
                            "file": <str>,              # filename (basename only) [changed in 2.0]
                            "location": {               # Location object [new in 2.0]
                                "url": <str>,           # HTTPS URL, OCI reference, or relative path
                                "size": <int>,          # file size in bytes
                                "checksum": <str>,      # "algorithm:hexdigest" format
                                "local_path": <str>     # full relative path for v1.x filesystem layout
                            }
                        }
                    ]
                }
            }
        }
    }


Examples
========

Fedora 41 extra files::

    {
        "header": {
            "type": "productmd.extra_files",
            "version": "2.0"
        },
        "payload": {
            "compose": {
                "date": "20260204",
                "id": "Fedora-41-20260204.0",
                "respin": 0,
                "type": "production"
            },
            "extra_files": {
                "Server": {
                    "x86_64": [
                        {
                            "file": "GPL",
                            "location": {
                                "url": "https://cdn.fedoraproject.org/.../Server/x86_64/os/GPL",
                                "size": 18092,
                                "checksum": "sha256:1f2a3b4c...",
                                "local_path": "Server/x86_64/os/GPL"
                            }
                        },
                        {
                            "file": "RPM-GPG-KEY-fedora-41-primary",
                            "location": {
                                "url": "https://cdn.fedoraproject.org/.../Server/x86_64/os/RPM-GPG-KEY-fedora-41-primary",
                                "size": 1714,
                                "checksum": "sha256:2a3b4c5d...",
                                "local_path": "Server/x86_64/os/RPM-GPG-KEY-fedora-41-primary"
                            }
                        }
                    ]
                }
            }
        }
    }
