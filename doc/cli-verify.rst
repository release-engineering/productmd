productmd-verify
================

Synopsis
--------

**productmd verify** [**--report** *FILE*] [**--quick**] [**--parallel-checksums** *N*] *input*

Description
-----------

Verify the integrity of compose metadata and local artifacts.  When
the input is a compose directory (or a file inside one), checks that
local files match the checksums and sizes recorded in the metadata.
In quick mode, only verifies that metadata files load and parse
correctly.

If the compose root cannot be determined from the input path, artifact
verification is skipped and only metadata loading is checked.

Options
-------

**--report** *FILE*
    Write verification results to a JSON file.  The report contains
    counts of verified, failed, and skipped artifacts, plus a list
    of errors with paths and failure reasons::

        {
            "verified": 42,
            "failed": 1,
            "skipped": 3,
            "errors": [
                {
                    "path": "Server/x86_64/iso/boot.iso",
                    "error": "checksum or size mismatch"
                }
            ]
        }

**--quick**
    Only verify that metadata loads correctly.  Skip artifact
    checksum and size verification.  Useful for a fast sanity check
    of metadata files without reading artifact data.

**--parallel-checksums** *N*
    Number of threads for parallel checksum verification (default: 4).
    Higher values improve throughput on SSDs and large composes.

*input*
    Path to a metadata file or compose directory.  Auto-detected.
    For full artifact verification, pass a compose directory or a
    metadata file inside a compose structure.

Examples
--------

Quick verification of metadata::

    productmd verify --quick images.json

Full verification of a compose directory::

    productmd verify /mnt/compose

Full verification with a JSON report::

    productmd verify --report verify-report.json /mnt/compose

See Also
--------

**productmd**\(1),
**productmd-localize**\(1)
