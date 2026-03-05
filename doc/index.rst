ProductMD library documentation
===============================
ProductMD is a Python library providing parsers for metadata
related to composes and installation media.

ProductMD supports multiple metadata format versions:

- **v1.x** (1.0, 1.1, 1.2): Local compose format with relative paths
- **v2.0**: Distributed compose format with Location objects (HTTPS URLs, OCI references)


Contents:

.. toctree::
    :maxdepth: 2

    terminology


Python modules:

.. toctree::
    :maxdepth: 2

    common
    compose
    composeinfo
    discinfo
    images
    rpms
    treeinfo


CLI Tools:

.. toctree::
    :maxdepth: 2

    cli-upgrade
    cli-downgrade
    cli-localize
    cli-verify


File formats (v1.1 -- local composes):

.. toctree::
    :maxdepth: 2

    composeinfo-1.1
    discinfo-1.0
    images-1.1
    rpms-1.1
    treeinfo-1.1

Old file formats:

.. toctree::
    :maxdepth: 1

    composeinfo-1.0
    images-1.0
    rpms-1.0
    treeinfo-1.0


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
