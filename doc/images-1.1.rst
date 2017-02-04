======================
Images file format 1.1
======================

images.json files provide details about images included in composes.


Changes from 1.0
================

* Added 'type' field to 'header', "productmd.images" required
* Added 'subvariant' field to image


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
            "type": "productmd.images",                 # metadata type; "productmd.images" required; [new in 1.1]
            "version": "1.1"                            # metadata version; format: $major<int>.$minor<int>
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
                            "checksums": {
                                type<str>: <str>        # 
                            },
                            "disc_count": <int>,        # number of discs in media set
                            "disc_number": <int>,       # disc number
                            "format": <str>,            # see productmd.images.SUPPORTED_IMAGE_FORMATS
                            "implant_md5": <str|null>,  # md5 checksum implanted directly on media (see implantisomd5 and checkisomd5 commands)
                            "mtime": <int>,             # mtime of the image stored as a decimal unix timestamp
                            "path": <str>,              # relative path to the image
                            "subvariant": <str>,        # image content (e.g. 'Workstation' or 'KDE'); [new in 1.1]
                            "size": <int>,              # file size of the image
                            "type": <str>,              # see productmd.images.SUPPORTED_IMAGE_TYPES
                            "volume_id": <str|null>     # volume ID; null if not available/applicable
                        }
                    ]
                }
            }
        }
    }
