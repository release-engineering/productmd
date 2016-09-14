===========================
Composeinfo file format 1.0
===========================

composeinfo.json files provide details about composes which includes
product information, variants, architectures and paths.


File Format
===========
Composeinfo is stored as a JSON serialized dictionary.
It's recommended to sort keys alphabetically and use 4 spaces for indentation
in order to read and diff composeinfo.json files easily.


::

    {
        "header": {
            "version": "1.0"                            # metadata version; format: $major<int>.$minor<int>
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
                "is_layered": <bool=false>,
            },
            "base_product": {
                "name": <str>,
                "version": <str>,
                "short": <str>,
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
