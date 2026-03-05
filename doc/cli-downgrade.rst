productmd-downgrade
===================

Synopsis
--------

**productmd downgrade** **--output** *DIR* *input*

Description
-----------

Downgrade v2.0 compose metadata to v1.2 format.  Loads v2.0 metadata,
converts Location objects back to simple path strings using the
``local_path`` field, and writes v1.2 metadata files to the output
directory.

This is a metadata-only operation — it does not download any artifacts.
The resulting v1.2 files contain relative paths suitable for a local
compose filesystem layout.

Options
-------

**--output** *DIR*
    Output directory for v1.2 metadata files.  Required.

*input*
    Path to a v2.0 metadata file or compose directory.  Auto-detected.

Examples
--------

Downgrade a single metadata file::

    productmd downgrade --output /tmp/v1 images.json

Downgrade all metadata from a compose directory::

    productmd downgrade --output /tmp/v1 /path/to/compose

See Also
--------

**productmd**\(1),
**productmd-upgrade**\(1)
