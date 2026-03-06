productmd-upgrade
=================

Synopsis
--------

**productmd upgrade** **--output** *DIR* [**--base-url** *URL*] [**--compute-checksums**] [**--strict-checksums**] [**--parallel-checksums** *N*] [**--url-map** *FILE*] *input*

Description
-----------

Upgrade v1.2 compose metadata to v2.0 format.  Loads metadata from a
single file or compose directory, creates Location objects for each
artifact with remote URLs and integrity information, and writes v2.0
metadata files to the output directory.

Each artifact's URL is constructed by prepending **--base-url** to the
local path, or by applying a custom URL mapping from **--url-map**.

Options
-------

**--output** *DIR*
    Output directory for v2.0 metadata files.  Required.

**--base-url** *URL*
    Base URL prefix prepended to local paths to form remote artifact URLs.
    For example, with ``--base-url https://cdn.example.com/compose/`` and
    a local path ``Server/x86_64/iso/boot.iso``, the URL becomes
    ``https://cdn.example.com/compose/Server/x86_64/iso/boot.iso``.

**--compute-checksums**
    Compute SHA-256 checksums from local files on disk.  The compose
    root is auto-detected from the input path.  When the input is a
    compose directory, the artifacts are located automatically.  When
    the input is a single metadata file inside a compose, the compose
    root is discovered from the file's location.  Without this flag,
    checksums are omitted from the v2.0 metadata.  If a file cannot
    be found, a warning is printed and the checksum is left empty.

**--strict-checksums**
    Error if any checksum cannot be computed (file not found).
    Implies **--compute-checksums**.  Useful in CI pipelines where
    all artifacts must be present and accounted for.

**--parallel-checksums** *N*
    Number of threads for parallel checksum computation (default: 4).
    Only applies when **--compute-checksums** or **--strict-checksums**
    is used.  Higher values improve throughput on SSDs and large
    composes with thousands of RPMs.

**--url-map** *FILE*
    Path to a JSON file with per-type URL mapping templates.
    Overrides **--base-url** for fine-grained control over URL
    construction by artifact type.

    The JSON file should contain string templates with placeholders::

        {
            "rpm": "https://cdn.example.com/rpms/{path}",
            "image": "https://cdn.example.com/images/{path}",
            "module": "https://cdn.example.com/modules/{path}",
            "extra_file": "https://cdn.example.com/extra/{path}",
            "variant_path": "https://cdn.example.com/repos/{path}",
            "default": "https://cdn.example.com/{path}"
        }

    Available placeholders:

    ``{path}``
        The artifact's local path (e.g., ``Server/x86_64/iso/boot.iso``).

    ``{variant}``
        The variant name (e.g., ``Server``).

    ``{arch}``
        The architecture (e.g., ``x86_64``).

    ``{metadata_type}``
        The artifact type (``rpm``, ``image``, ``module``, ``extra_file``,
        ``variant_path``).

    If no template matches the artifact type, the ``default`` template
    is used.

*input*
    Path to a v1.2 metadata file or compose directory.  Auto-detected.

Examples
--------

Upgrade a compose directory with a base URL::

    productmd upgrade \
        --output /tmp/v2 \
        --base-url https://cdn.example.com/compose/ \
        /mnt/compose

Upgrade with checksum computation::

    productmd upgrade \
        --output /tmp/v2 \
        --base-url https://cdn.example.com/ \
        --compute-checksums \
        /mnt/compose

Upgrade a single images.json file::

    productmd upgrade \
        --output /tmp/v2 \
        --base-url https://cdn.example.com/ \
        images.json

Upgrade with custom URL mapping::

    productmd upgrade \
        --output /tmp/v2 \
        --url-map url-templates.json \
        /mnt/compose

See Also
--------

**productmd**\(1),
**productmd-downgrade**\(1)
