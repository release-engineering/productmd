======================
Images file format 2.0
======================

images.json files provide details about images included in composes.


Changes from 1.1
=================

* ``path``, ``size``, and ``checksums`` fields replaced by a single ``location`` object
* Location objects include ``url``, ``size``, ``checksum``, ``local_path``, and optional ``contents``
* URLs may be HTTPS URLs, OCI registry references, or relative paths
* OCI images may include a ``contents`` array describing individual files as layers
* Checksums use ``algorithm:hexdigest`` format (e.g., ``sha256:abc123...``)
* ``force_version`` parameter added to ``serialize()`` for version control


Location Object
===============

Each image entry contains a ``location`` object instead of separate ``path``,
``size``, and ``checksums`` fields. The ``location.local_path`` preserves the
v1.x relative path for backward-compatible filesystem layout.

For OCI images that bundle multiple files (e.g., boot images with kernel, initrd,
efiboot.img), the ``contents`` array provides per-file metadata including the
OCI layer digest. See :class:`~productmd.location.FileEntry` for details.


File Format
===========

Compose images metadata is stored as a JSON serialized dictionary.
It's recommended to sort keys alphabetically and use 4 spaces for indentation
in order to read and diff images.json files easily.

Image Identity
==============

It is required that the combination of subvariant, type, format, arch and
disc_number attributes is unique to each image in the compose. This is to
ensure these attributes can be used to identify 'the same' image across
composes. This may require including the variant string in the subvariant.

::

    {
        "header": {
            "type": "productmd.images",                 # metadata type; "productmd.images" required
            "version": "2.0"                            # metadata version; format: $major<int>.$minor<int>
        },
        "payload": {
            "compose": {                                # see composeinfo for details
                "date": <str>,
                "id": <str>,
                "respin": <int>,
                "type": <str>
            },
            "images": {
                variant_uid<str>: {                     # compose variant UID
                    arch<str>: [                        # compose variant arch
                        {
                            "arch": <str>,              # image arch
                            "bootable": <bool>,         # can the image be booted?
                            "disc_count": <int>,        # number of discs in media set
                            "disc_number": <int>,       # disc number
                            "format": <str>,            # see productmd.images.SUPPORTED_IMAGE_FORMATS
                            "implant_md5": <str|null>,  # md5 checksum implanted directly on media
                            "mtime": <int>,             # mtime as a decimal unix timestamp
                            "subvariant": <str>,        # image content (e.g. 'Workstation' or 'KDE')
                            "type": <str>,              # see productmd.images.SUPPORTED_IMAGE_TYPES
                            "volume_id": <str|null>,    # volume ID; null if not available/applicable
                            "location": {               # Location object [new in 2.0]
                                "url": <str>,           # HTTPS URL, OCI reference, or relative path
                                "size": <int>,          # file size in bytes
                                "checksum": <str>,      # "algorithm:hexdigest" format
                                "local_path": <str>,    # relative path for v1.x filesystem layout
                                "contents": [           # optional; for OCI images with multiple files
                                    {
                                        "file": <str>,          # relative path within the image
                                        "size": <int>,          # file size in bytes
                                        "checksum": <str>,      # "algorithm:hexdigest" format
                                        "layer_digest": <str>   # OCI layer digest (sha256:...)
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
    }


Examples
========

Fedora 41 Server images with HTTPS and OCI URLs::

    {
        "header": {
            "type": "productmd.images",
            "version": "2.0"
        },
        "payload": {
            "compose": {
                "date": "20260204",
                "id": "Fedora-41-20260204.0",
                "respin": 0,
                "type": "production"
            },
            "images": {
                "Server": {
                    "x86_64": [
                        {
                            "arch": "x86_64",
                            "bootable": true,
                            "disc_count": 1,
                            "disc_number": 1,
                            "format": "iso",
                            "implant_md5": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6",
                            "mtime": 1738627200,
                            "subvariant": "",
                            "type": "dvd",
                            "volume_id": "Fedora-S-41-x86_64",
                            "location": {
                                "url": "https://cdn.fedoraproject.org/.../Fedora-Server-dvd-x86_64-41-1.1.iso",
                                "size": 2465792000,
                                "checksum": "sha256:1a2b3c4d...",
                                "local_path": "Server/x86_64/iso/Fedora-Server-dvd-x86_64-41-1.1.iso"
                            }
                        },
                        {
                            "arch": "x86_64",
                            "bootable": false,
                            "format": "qcow2",
                            "mtime": 1738627200,
                            "subvariant": "",
                            "type": "qcow2",
                            "volume_id": null,
                            "location": {
                                "url": "oci://quay.io/fedora/server:41-x86_64@sha256:3c4d5e6f...",
                                "size": 512000000,
                                "checksum": "sha256:3c4d5e6f...",
                                "local_path": "Server/x86_64/images/Fedora-Server-41-1.1.x86_64.qcow2"
                            }
                        }
                    ]
                }
            }
        }
    }
