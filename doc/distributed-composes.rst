====================================
Distributed Composes: Use Cases
====================================

This document describes common deployment patterns for distributed composes
using productmd v2.0.


What is a Distributed Compose?
==============================

In a traditional (v1.2) compose, all artifacts live on a single filesystem
under a well-known directory structure::

    compose/
      Server/
        x86_64/
          iso/boot.iso
          os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm
      metadata/
        images.json
        rpms.json

In a **distributed compose** (v2.0), the metadata files still describe the
same logical compose, but artifacts can be stored anywhere -- CDNs, object
storage, OCI registries, or a mix of all three.  The metadata uses Location
objects with URLs instead of relative paths.

The ``local_path`` field in each Location preserves the v1.2 directory
layout, so a distributed compose can be **localized** back to a traditional
filesystem layout at any time.


Use Case 1: CDN-Hosted Composes
================================

Artifacts are uploaded to a CDN during the compose process.  The v2.0
metadata references them via HTTPS URLs.

**Workflow:**

1. Build system (e.g., pungi) creates artifacts on local storage
2. Artifacts are uploaded to CDN (e.g., ``cdn.fedoraproject.org``)
3. v1.2 metadata is upgraded to v2.0 with CDN base URL
4. v2.0 metadata is published (to the CDN or a separate metadata service)

**Upgrade command:**

.. code-block:: bash

    productmd upgrade \
        --output /tmp/v2-metadata \
        --base-url https://cdn.fedoraproject.org/compose/41/ \
        --compute-checksums \
        /mnt/compose

**Localize (mirror) command:**

.. code-block:: bash

    productmd localize \
        --output /mnt/mirror \
        --parallel-downloads 16 \
        --skip-existing \
        images.json


Use Case 2: OCI Registry Storage
==================================

Artifacts are pushed to an OCI registry using ``oras push``.  The v2.0
metadata references them via ``oci://`` URLs.

This is useful for:

- Storing artifacts alongside container images in the same registry
- Leveraging existing registry infrastructure and access controls
- Enabling distribution via OCI distribution spec (pull from any
  OCI-compatible client)

**Pushing artifacts:**

.. code-block:: bash

    # Push an ISO to the registry
    oras push quay.io/fedora/server:41-x86_64 \
        Server/x86_64/iso/boot.iso

    # The resulting digest is used in the metadata URL:
    # oci://quay.io/fedora/server:41-x86_64@sha256:1a2b3c4d...

**Localize from OCI:**

.. code-block:: bash

    # Requires oras-py: pip install productmd[oci]
    # Authenticate first: podman login quay.io
    productmd localize \
        --output /mnt/local \
        --parallel-downloads 4 \
        images.json


Use Case 3: Mixed Storage
==========================

Different artifact types are stored on different backends.  For example,
ISOs on a CDN and RPMs in an OCI registry:

.. code-block:: json

    {
        "image": "https://cdn.example.com/images/{path}",
        "rpm": "oci://registry.example.com/rpms:{variant}-{arch}",
        "default": "https://cdn.example.com/{path}"
    }

The localization tool handles both HTTPS and OCI downloads transparently,
running them in parallel.


Use Case 4: Multi-Site Mirroring
=================================

A compose is produced at a central site and needs to be mirrored to
multiple edge locations.  Each mirror site runs localization independently:

**Central site:**

.. code-block:: bash

    # Produce v2.0 metadata pointing to the origin CDN
    productmd upgrade \
        --output /shared/metadata \
        --base-url https://origin.example.com/compose/ \
        /mnt/compose

**Each mirror site:**

.. code-block:: bash

    # Download the compose to local storage
    productmd localize \
        --output /mnt/local-mirror \
        --parallel-downloads 32 \
        --skip-existing \
        /shared/metadata/images.json

    # Verify integrity after download
    productmd verify /mnt/local-mirror

The ``--skip-existing`` flag makes subsequent runs incremental -- only
new or changed artifacts are downloaded.


Use Case 5: CI/CD Pipeline Integration
========================================

In a CI/CD pipeline, compose metadata can be generated as v2.0 from
the start, with artifacts uploaded to object storage as they're built:

.. code-block:: python

    from productmd.images import Images, Image
    from productmd.location import Location
    from productmd.version import VERSION_2_0

    images = Images()
    images.output_version = VERSION_2_0
    images.compose.id = "MyProduct-1.0-20260204.0"
    images.compose.type = "nightly"
    images.compose.date = "20260204"
    images.compose.respin = 0

    # After uploading each artifact, add it to the metadata
    image = Image(images)
    image.arch = "x86_64"
    image.type = "qcow2"
    image.format = "qcow2"
    image.subvariant = "Server"
    image.disc_number = 1
    image.disc_count = 1
    image.location = Location(
        url=f"https://builds.example.com/{upload_path}",
        size=os.path.getsize(local_file),
        checksum=compute_checksum(local_file, "sha256"),
        local_path=relative_path,
    )
    images.add("Server", "x86_64", image)

    # Publish metadata (no need to upload artifacts separately)
    images.dump("images.json")


Localization Workflow
=====================

The ``productmd localize`` command (or :func:`~productmd.localize.localize_compose`
function) downloads a distributed compose to local storage:

1. **Collect** -- Scans metadata for all remote Location objects
2. **Deduplicate** -- Removes duplicate download tasks (same URL)
3. **Skip** -- With ``--skip-existing``, skips files already present
   with matching checksums
4. **Download** -- Fetches artifacts in parallel (HTTP and OCI)
5. **Verify** -- Checks checksums after each download
6. **Write metadata** -- Produces v1.2 metadata files in the output
   directory under ``compose/metadata/``

The result is a standard v1.2 compose layout that works with existing
tools (Anaconda, lorax, pungi).

.. code-block:: text

    output/
      compose/
        Server/
          x86_64/
            iso/boot.iso          <-- downloaded from HTTPS or OCI
            os/Packages/b/bash-*.rpm
        metadata/
          images.json             <-- v1.2 format
          rpms.json
          composeinfo.json


See Also
========

- :doc:`productmd-2.0` -- Complete v2.0 format specification
- :doc:`migration-guide` -- Step-by-step migration from v1.2
- :doc:`cli-localize` -- Localize command reference
- :doc:`cli-verify` -- Verify command reference
