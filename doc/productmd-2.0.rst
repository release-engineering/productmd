===================================
ProductMD 2.0 Format Specification
===================================

Overview
========

ProductMD 2.0 introduces support for **distributed composes** where artifacts
(RPMs, images, repositories) can be stored in different locations and
referenced via HTTPS URLs or OCI registry references.  The metadata includes
checksums for data integrity verification and supports bidirectional conversion
between v2.0 (distributed) and v1.2 (local) formats.

Key changes from v1.2:

- Raw path strings are replaced by **Location objects** containing a URL,
  size, checksum, and a ``local_path`` hint for the v1.2 filesystem layout
- URLs can be HTTPS, HTTP, or ``oci://`` references to OCI registries
- Checksums use ``algorithm:hexdigest`` format (e.g., ``sha256:abc123...``)
- OCI images can include a ``contents`` array describing individual files
  as layers within a single OCI artifact
- Full backward compatibility: v2.0 metadata can be downgraded to v1.2 and
  v1.2 can be upgraded to v2.0


Location Object
===============

The Location object is the core addition in v2.0.  It replaces raw path strings
throughout the metadata with a structured object containing remote access
information and integrity data.

.. code-block:: json

    {
        "url": "https://cdn.example.com/Server/x86_64/iso/boot.iso",
        "size": 2465792000,
        "checksum": "sha256:1a2b3c4d5e6f...",
        "local_path": "Server/x86_64/iso/boot.iso"
    }

Fields:

``url``
    Remote location of the artifact.  Supported schemes:

    - ``https://`` / ``http://`` -- Direct download URLs
    - ``oci://`` -- OCI registry references in the format
      ``oci://registry/repository:tag@sha256:digest``

``size``
    File size in bytes.  Used for download progress and verification.

``checksum``
    Integrity hash in ``algorithm:hexdigest`` format.  SHA-256 is the
    default algorithm.

``local_path``
    Relative path within the v1.2 compose filesystem layout.  Used when
    downgrading to v1.2 format or when localizing a distributed compose.

``contents`` *(optional, images only)*
    Array of :class:`~productmd.location.FileEntry` objects describing
    individual files within an OCI artifact.  Each entry specifies the
    file path, size, checksum, and OCI layer digest.

See :class:`~productmd.location.Location` and
:class:`~productmd.location.FileEntry` for the full Python API.


URL Schemes
===========

HTTPS/HTTP
----------

Standard HTTP URLs pointing to artifact files on CDNs, web servers, or
object storage.  These are downloaded directly by the localization tool.

Example::

    https://cdn.fedoraproject.org/compose/41/Server/x86_64/iso/boot.iso

OCI Registry References
-----------------------

OCI references use the ``oci://`` scheme and follow the standard OCI
distribution reference format::

    oci://registry/repository:tag@sha256:digest

Examples::

    oci://quay.io/fedora/server:41-x86_64@sha256:1a2b3c4d...
    oci://registry.example.com/composes/f41:server-rpms@sha256:5e6f7a8b...

OCI support requires the ``oras-py`` package::

    pip install productmd[oci]

Authentication uses standard Docker and Podman credential stores
(``docker login`` / ``podman login``).


Metadata Files
==============

The v2.0 format applies to five metadata files:

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - File
     - Key Change
     - Format Spec
   * - ``composeinfo.json``
     - Variant paths become Location objects
     - :doc:`composeinfo-2.0`
   * - ``images.json``
     - ``path`` + ``checksums`` replaced by ``location``
     - :doc:`images-2.0`
   * - ``rpms.json``
     - ``path`` replaced by ``location``
     - :doc:`rpms-2.0`
   * - ``extra_files.json``
     - ``size`` + ``checksums`` replaced by ``location``
     - :doc:`extra_files-2.0`
   * - ``modules.json``
     - Flattened structure, ``modulemd_path`` replaced by ``location``
     - :doc:`modules-2.0`

**Not changed:** ``.treeinfo`` files remain at v1.2 format.  They are
generated during localization, not stored as v2.0 metadata.


Version Detection
=================

The format version is indicated in the ``header.version`` field of each
metadata file:

.. code-block:: json

    {
        "header": {
            "type": "productmd.images",
            "version": "2.0"
        }
    }

The library automatically detects the version during deserialization and
selects the appropriate parser.  See :func:`~productmd.version.detect_version_from_data`
and :class:`~productmd.version.VersionedMetadataMixin` for details.


Checksum Format
===============

All checksums in v2.0 use the ``algorithm:hexdigest`` format:

.. code-block:: text

    sha256:1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b

This format is self-describing -- the algorithm is encoded in the string
itself.  The default algorithm is SHA-256, but the format supports any
algorithm recognized by Python's ``hashlib`` module.

Checksums can be computed using :func:`~productmd.location.compute_checksum`
and parsed using :func:`~productmd.location.parse_checksum`.


Backward Compatibility
======================

v2.0 is designed for full backward compatibility:

**Deserialization:** The library automatically detects whether a metadata file
is v1.2 or v2.0 and selects the appropriate parser.  v1.2 metadata loads
without any changes to existing code.

**Serialization:** The output version is controlled by
:attr:`~productmd.version.VersionedMetadataMixin.output_version`.  By default
it is set to ``VERSION_2_0``, but can be overridden:

.. code-block:: python

    from productmd.images import Images
    from productmd.version import VERSION_1_2

    images = Images()
    images.deserialize(v2_data)
    images.output_version = VERSION_1_2
    images.serialize(data)  # writes v1.2 format

**Round-trip fidelity:** Loading a v1.2 file and saving it preserves the
original format version -- the ``output_version`` is set from the loaded
file's version.

**Conversion tools:** The :func:`~productmd.convert.upgrade_to_v2` and
:func:`~productmd.convert.downgrade_to_v1` functions handle bulk conversion
of all metadata files in a compose.


See Also
========

- :doc:`migration-guide` -- Step-by-step migration from v1.2 to v2.0
- :doc:`distributed-composes` -- Use cases and deployment patterns
- :doc:`cli` -- CLI tools for conversion, localization, and verification
