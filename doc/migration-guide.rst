==============================
v1.2 to v2.0 Migration Guide
==============================

This guide covers migrating from productmd v1.2 to v2.0 format, both for
**compose producers** (tools like pungi that generate metadata) and
**compose consumers** (tools that read metadata).


Reading v2.0 Metadata (Consumers)
=================================

No code changes required
------------------------

The productmd library automatically detects the format version and
deserializes correctly.  Existing code that reads v1.2 metadata will
work with v2.0 files without modification:

.. code-block:: python

    from productmd.images import Images

    # This works for both v1.2 and v2.0 files
    images = Images()
    images.load("images.json")

    for variant in images.images:
        for arch in images.images[variant]:
            for image in images.images[variant][arch]:
                print(image.path)      # always available
                print(image.checksums)  # always available

The v1.2 compatibility fields (``path``, ``size``, ``checksums``) are
populated from the Location object during deserialization, so existing
code continues to work.


Accessing Location objects
--------------------------

To take advantage of v2.0 features (remote URLs, checksums, OCI
references), access the ``location`` property:

.. code-block:: python

    from productmd.images import Images

    images = Images()
    images.load("images.json")

    for variant in images.images:
        for arch in images.images[variant]:
            for image in images.images[variant][arch]:
                loc = image.location
                print(loc.url)         # "https://cdn.example.com/..."
                print(loc.checksum)    # "sha256:abc123..."
                print(loc.size)        # 2465792000
                print(loc.local_path)  # "Server/x86_64/iso/boot.iso"
                print(loc.is_oci)      # True if oci:// URL
                print(loc.is_remote)   # True if http/https/oci URL

For v1.2 files, ``image.location`` synthesizes a Location from the v1.2
fields (``path``, ``size``, ``checksums``) with no remote URL.


Iterating all locations
-----------------------

Use :func:`~productmd.convert.iter_all_locations` to iterate over every
artifact location across all metadata types:

.. code-block:: python

    from productmd.compose import Compose
    from productmd.convert import iter_all_locations

    compose = Compose("/path/to/compose")
    for entry in iter_all_locations(
        images=compose.images,
        rpms=compose.rpms,
        extra_files=compose.extra_files,
        composeinfo=compose.info,
    ):
        print(f"{entry.metadata_type}: {entry.path}")
        if entry.location and entry.location.is_remote:
            print(f"  URL: {entry.location.url}")


Writing v2.0 Metadata (Producers)
==================================

Upgrading existing v1.2 composes
--------------------------------

The simplest way to create v2.0 metadata is to upgrade existing v1.2
files using the CLI tool:

.. code-block:: bash

    # Upgrade a compose directory
    productmd upgrade \
        --output /tmp/v2-metadata \
        --base-url https://cdn.example.com/compose/ \
        /mnt/compose

    # Upgrade with checksum computation
    productmd upgrade \
        --output /tmp/v2-metadata \
        --base-url https://cdn.example.com/compose/ \
        --compute-checksums \
        /mnt/compose

Or programmatically:

.. code-block:: python

    from productmd.compose import Compose
    from productmd.convert import upgrade_to_v2

    compose = Compose("/mnt/compose")
    upgrade_to_v2(
        output_dir="/tmp/v2-metadata",
        base_url="https://cdn.example.com/compose/",
        images=compose.images,
        rpms=compose.rpms,
        extra_files=compose.extra_files,
        composeinfo=compose.info,
    )


Creating v2.0 metadata from scratch
------------------------------------

When generating new compose metadata, create Location objects directly:

.. code-block:: python

    from productmd.images import Images, Image
    from productmd.location import Location
    from productmd.version import VERSION_2_0

    images = Images()
    images.header.version = "2.0"
    images.compose.id = "Fedora-41-20260204.0"
    images.compose.type = "production"
    images.compose.date = "20260204"
    images.compose.respin = 0
    images.output_version = VERSION_2_0

    image = Image(images)
    image.arch = "x86_64"
    image.type = "dvd"
    image.format = "iso"
    image.subvariant = "Server"
    image.disc_number = 1
    image.disc_count = 1
    image.mtime = 1738627200
    image.volume_id = "Fedora-S-41-x86_64"
    image.location = Location(
        url="https://cdn.example.com/Server/x86_64/iso/boot.iso",
        size=2465792000,
        checksum="sha256:1a2b3c4d5e6f...",
        local_path="Server/x86_64/iso/boot.iso",
    )

    images.add("Server", "x86_64", image)
    images.dump("images.json")


Adding Locations to RPMs
------------------------

.. code-block:: python

    from productmd.rpms import Rpms
    from productmd.location import Location
    from productmd.version import VERSION_2_0

    rpms = Rpms()
    rpms.compose.id = "Fedora-41-20260204.0"
    rpms.compose.type = "production"
    rpms.compose.date = "20260204"
    rpms.compose.respin = 0
    rpms.output_version = VERSION_2_0

    rpms.add(
        variant="Server",
        arch="x86_64",
        nevra="bash-0:5.2.26-3.fc41.x86_64",
        path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
        sigkey="a15b79cc",
        category="binary",
        srpm_nevra="bash-0:5.2.26-3.fc41.src",
        location=Location(
            url="https://cdn.example.com/Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
            size=1849356,
            checksum="sha256:6a7b8c9d...",
            local_path="Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
        ),
    )


Custom URL mapping
------------------

For composes where different artifact types are stored on different servers,
use a URL mapper:

.. code-block:: python

    from productmd.convert import upgrade_to_v2

    def my_url_mapper(local_path, variant, arch, metadata_type):
        if metadata_type == "image":
            return f"https://images.example.com/{local_path}"
        elif metadata_type == "rpm":
            return f"https://rpms.example.com/{local_path}"
        else:
            return f"https://cdn.example.com/{local_path}"

    upgrade_to_v2(
        output_dir="/tmp/v2",
        url_mapper=my_url_mapper,
        images=compose.images,
        rpms=compose.rpms,
    )

Or via the CLI with a JSON template file:

.. code-block:: json

    {
        "image": "https://images.example.com/{path}",
        "rpm": "https://rpms.example.com/{path}",
        "default": "https://cdn.example.com/{path}"
    }

.. code-block:: bash

    productmd upgrade --output /tmp/v2 --url-map templates.json /mnt/compose


Downgrading back to v1.2
=========================

v2.0 metadata can be converted back to v1.2 at any time.  The
``local_path`` field is used as the ``path`` value in the v1.2 output:

.. code-block:: bash

    productmd downgrade --output /tmp/v1 images.json

Programmatically:

.. code-block:: python

    from productmd.convert import downgrade_to_v1

    downgrade_to_v1(
        output_dir="/tmp/v1",
        images=images,
        rpms=rpms,
    )


Verifying integrity
===================

After localization or manual download, verify that local files match the
metadata checksums:

.. code-block:: bash

    # Quick check (metadata only)
    productmd verify --quick images.json

    # Full check (verifies all artifact checksums)
    productmd verify /mnt/local-compose

    # Save results to JSON
    productmd verify --report results.json /mnt/local-compose

Programmatically, use the Location's verify methods:

.. code-block:: python

    from productmd.location import Location

    loc = image.location
    if loc.verify("/mnt/compose/Server/x86_64/iso/boot.iso"):
        print("Checksum and size match")


See Also
========

- :doc:`productmd-2.0` -- Complete v2.0 format specification
- :doc:`distributed-composes` -- Use cases and deployment patterns
- :doc:`cli` -- CLI tool reference
