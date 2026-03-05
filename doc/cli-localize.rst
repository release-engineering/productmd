productmd-localize
==================

Synopsis
--------

**productmd localize** **--output** *DIR* [**--parallel-downloads** *N*] [**--no-verify-checksums**] [**--skip-existing**] [**--retries** *N*] [**--no-fail-fast**] *input*

Description
-----------

Download all remote artifacts from a v2.0 compose to local storage,
recreating the standard v1.2 filesystem layout.  After downloading,
writes v1.2 metadata files to the output directory.

Supports both HTTPS/HTTP and OCI registry downloads.  HTTP downloads
run in parallel using a thread pool.  OCI downloads also run in parallel,
with each thread using its own registry connection for thread safety.

After all downloads complete, v1.2 metadata files are written to
``<output>/compose/metadata/``.

Options
-------

**--output** *DIR*
    Local directory to create the compose layout.  Required.
    The compose tree is created under ``<DIR>/compose/``.

**--parallel-downloads** *N*
    Number of concurrent download threads.  Default: 4.
    Applies to both HTTP and OCI downloads.  Set to 1 for sequential
    downloads.

**--no-verify-checksums**
    Skip SHA-256 checksum verification after each download.
    By default, checksums are verified and mismatches cause an error.

**--skip-existing**
    Skip files that already exist on disk.  When combined with
    checksum verification (the default), only skips files whose
    checksums match the metadata.  Useful for resuming interrupted
    downloads.

**--retries** *N*
    Number of retry attempts per HTTP download.  Default: 3.
    Uses exponential backoff between retries (1s, 2s, 4s, ...).
    Does not apply to OCI downloads (oras-py handles its own retries).

**--no-fail-fast**
    Continue downloading after failures instead of stopping on the
    first error.  By default, the tool stops immediately when any
    download fails.  With this flag, all errors are collected and
    reported at the end.

*input*
    Path to a v2.0 metadata file or compose directory.  Auto-detected.

OCI Support
-----------

Artifacts stored in OCI registries (URLs starting with ``oci://``)
require the **oras-py** package::

    pip install productmd[oci]

Authentication uses standard Docker and Podman credential stores.
Run ``docker login`` or ``podman login`` before using **productmd
localize** with OCI registry URLs.  Credentials are discovered from
the following locations in order:

1. ``$REGISTRY_AUTH_FILE`` (Podman/Skopeo)
2. ``$XDG_RUNTIME_DIR/containers/auth.json`` (Podman runtime)
3. ``$XDG_CONFIG_HOME/containers/auth.json`` (Podman persistent)
4. ``$DOCKER_CONFIG/config.json`` (Docker env override)
5. ``~/.docker/config.json`` (Docker default)

If OCI URLs are present in the metadata but oras-py is not installed,
the tool exits with an error message.

Examples
--------

Download a distributed compose::

    productmd localize \
        --output /mnt/local \
        --parallel-downloads 8 \
        images.json

Resume an interrupted download::

    productmd localize \
        --output /mnt/local \
        --skip-existing \
        images.json

Download without checksum verification::

    productmd localize \
        --output /mnt/local \
        --no-verify-checksums \
        images.json

Continue after failures::

    productmd localize \
        --output /mnt/local \
        --no-fail-fast \
        images.json

See Also
--------

**productmd**\(1),
**productmd-upgrade**\(1),
**productmd-verify**\(1)
