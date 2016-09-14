===========================
Composeinfo file format 1.1
===========================

composeinfo.json files provide details about composes which includes
product information, variants, architectures and paths.


Changes from 1.0
================

* Added 'type' field to 'header', "productmd.composeinfo" required
* Added 'type' field to 'release'
* Added 'type' field to 'base_product'


File Format
===========
Composeinfo is stored as a JSON serialized dictionary.
It's recommended to sort keys alphabetically and use 4 spaces for indentation
in order to read and diff composeinfo.json files easily.


::

    {
        "header": {
            "type": "productmd.composeinfo",            # metadata type; "productmd.composeinfo" required; [new in 1.1]
            "version": "1.1"                            # metadata version; format: $major<int>.$minor<int>
        },
        "payload": {
            "compose": {
                "id": <str>,
                "date": <str>,
                "respin": <int>,
                "type": <str>,
                "label": <str|unset>,
                "final": <bool=false>                   # true if a compose is final for a milestone (for example latest Beta-1.x)
            },
            "release": {
                "name": <str>,
                "version": <str>,
                "short": <str>,
                "type": <str>,                          # [new in 1.1]
                "is_layered": <bool=false>,
            },
            "base_product": {
                "name": <str>,
                "version": <str>,
                "short": <str>,
                "type": <str>,                          # [new in 1.1]
            },
            "variants": {
                variant_uid<str>: {
                    "id": <str>,
                    "uid": <str>,
                    "name": <str>,
                    "type": <str>,
                    "arches": [<str>],
                    "paths": {
                        path_category<str>: {
                            arch<str>: <str>,
                        },
                    },
                },
            },
        },
    }
