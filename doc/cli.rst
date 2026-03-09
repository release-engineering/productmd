productmd
=========

Synopsis
--------

**productmd** *command* [*options*] *input*

Description
-----------

**productmd** is a command-line tool for managing compose metadata.  It
supports upgrading metadata from v1.2 to v2.0 format, downgrading back
to v1.2, downloading distributed v2.0 composes to local storage, and
verifying compose integrity.

The v2.0 format replaces raw path strings with Location objects
containing URLs, checksums, sizes, and local path hints.  This enables
distributed composes where artifacts are stored on CDNs or OCI registries
rather than a single filesystem.

Input Auto-Detection
--------------------

*input*
    Path to a metadata file or compose directory.  The tool auto-detects
    whether the input is a file or directory.  If a directory, it is
    scanned for compose metadata (``composeinfo.json`` or
    ``metadata/composeinfo.json``).  If a single file, the tool also
    tries to discover a compose root from the file's location.  Remote
    URLs are not supported.

Commands
--------

**productmd upgrade**
    Upgrade v1.2 compose metadata to v2.0 format.
    See **productmd-upgrade**\(1).

**productmd downgrade**
    Downgrade v2.0 compose metadata to v1.2 format.
    See **productmd-downgrade**\(1).

**productmd localize**
    Download a distributed v2.0 compose to local storage.
    See **productmd-localize**\(1).

**productmd verify**
    Verify integrity of compose metadata and local artifacts.
    See **productmd-verify**\(1).

Exit Status
-----------

**0**
    Success.

**1**
    Error (invalid input, download failure, verification failure).

**130**
    Interrupted by the user (Ctrl+C).

Examples
--------

Upgrade a local v1.2 compose to v2.0::

    productmd upgrade --output /tmp/v2 --base-url https://cdn.example.com/ /mnt/compose

Downgrade a single v2.0 metadata file to v1.2::

    productmd downgrade --output /tmp/v1 images.json

Download a distributed compose::

    productmd localize --output /mnt/local --parallel-downloads 8 images.json

Verify a local compose::

    productmd verify /mnt/compose

See Also
--------

**productmd-upgrade**\(1),
**productmd-downgrade**\(1),
**productmd-localize**\(1),
**productmd-verify**\(1)
