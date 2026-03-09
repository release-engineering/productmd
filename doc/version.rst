================================================
version -- Version detection and handling
================================================

.. automodule:: productmd.version


Constants
=========

.. autodata:: productmd.version.VERSION_1_0

.. autodata:: productmd.version.VERSION_1_1

.. autodata:: productmd.version.VERSION_1_2

.. autodata:: productmd.version.VERSION_2_0

.. autodata:: productmd.version.OUTPUT_FORMAT_VERSION


Functions
=========

.. autofunction:: productmd.version.version_to_string

.. autofunction:: productmd.version.string_to_version

.. autofunction:: productmd.version.get_version_tuple

.. autofunction:: productmd.version.is_v1

.. autofunction:: productmd.version.is_v2

.. autofunction:: productmd.version.supports_location_objects

.. autofunction:: productmd.version.detect_version_from_data


Classes
=======

.. autoclass:: productmd.version.VersionedMetadataMixin
   :members:

.. autoclass:: productmd.version.VersionError
   :members:

.. autoclass:: productmd.version.UnsupportedVersionError
   :members:
