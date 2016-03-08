===========================================
common -- Base classes and common functions
===========================================

.. automodule:: productmd.common


Constants
=========

.. _RELEASE_TYPES:
.. autodata:: productmd.common.RELEASE_TYPES

.. autodata:: productmd.common.RELEASE_SHORT_RE

.. autodata:: productmd.common.RELEASE_VERSION_RE


Functions
=========

.. autofunction:: productmd.common.parse_nvra

.. autofunction:: productmd.common.create_release_id

.. autofunction:: productmd.common.parse_release_id

.. autofunction:: productmd.common.is_valid_release_short

.. autofunction:: productmd.common.is_valid_release_version

.. autofunction:: productmd.common.split_version

.. autofunction:: productmd.common.get_major_version

.. autofunction:: productmd.common.get_minor_version


Classes
=======

.. autoclass:: productmd.common.MetadataBase
   :members:

.. autoclass:: productmd.common.Header
   :members:
