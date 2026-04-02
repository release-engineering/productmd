"""
Conversion utilities for productmd metadata formats.

Provides functions to iterate over all artifact locations in compose
metadata, upgrade v1.x metadata to v2.0 with Location objects, and
downgrade v2.0 metadata back to v1.2.

Example::

    from productmd.compose import Compose
    from productmd.convert import upgrade_to_v2, downgrade_to_v1

    compose = Compose("/path/to/v1.2-compose")
    result = upgrade_to_v2(
        output_dir="/tmp/v2-metadata",
        images=compose.images,
        rpms=compose.rpms,
        base_url="https://cdn.example.com/compose/",
    )

    # Or downgrade v2.0 back to v1.2
    downgrade_to_v1(
        output_dir="/tmp/v1-metadata",
        images=result["images"],
        rpms=result["rpms"],
    )
"""

import os
import warnings
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from typing import Callable, Dict, Iterator, Optional, Tuple

from productmd.location import Location, compute_checksum
from productmd.version import VERSION_1_2, VERSION_2_0


__all__ = (
    "LocationEntry",
    "MetadataType",
    "iter_all_locations",
    "upgrade_to_v2",
    "downgrade_to_v1",
)


class MetadataType(str, Enum):
    """Type of metadata entry in a compose.

    Inherits from ``str`` so values can be compared directly with
    plain strings (e.g., ``entry.metadata_type == "image"``).
    """

    IMAGE = "image"
    RPM = "rpm"
    EXTRA_FILE = "extra_file"
    MODULE = "module"
    VARIANT_PATH = "variant_path"


LocationEntry = namedtuple(
    "LocationEntry",
    [
        "metadata_type",
        "variant",
        "arch",
        "path",
        "location",
        "set_location",
        "field_name",
    ],
)
# INFO: Using __new__.__defaults__ instead of namedtuple(defaults=...)
# because the defaults parameter requires Python 3.7+.
LocationEntry.__new__.__defaults__ = (None,)
"""
A single artifact location from compose metadata.

:param metadata_type: :class:`MetadataType` indicating the kind of artifact
:param variant: Variant UID
:param arch: Architecture
:param path: Relative path to the artifact
:param location: :class:`~productmd.location.Location` object, or ``None`` for v1.x data
:param set_location: Callable that sets a new Location on the source object
:param field_name: For variant paths, the field name (e.g., ``"repository"``).
    ``None`` for non-variant-path entries.
"""


def iter_all_locations(
    images: Optional[object] = None,
    rpms: Optional[object] = None,
    extra_files: Optional[object] = None,
    modules: Optional[object] = None,
    composeinfo: Optional[object] = None,
) -> Iterator[LocationEntry]:
    """
    Yield all artifact locations from compose metadata.

    Iterates over all artifacts across the provided metadata objects,
    yielding a :class:`LocationEntry` for each. Each entry includes a
    ``set_location`` callback that can be used to attach a new
    :class:`~productmd.location.Location` to the source object.

    :param images: :class:`~productmd.images.Images` instance
    :param rpms: :class:`~productmd.rpms.Rpms` instance
    :param extra_files: :class:`~productmd.extra_files.ExtraFiles` instance
    :param modules: :class:`~productmd.modules.Modules` instance
    :param composeinfo: :class:`~productmd.composeinfo.ComposeInfo` instance
    :return: Iterator of :class:`LocationEntry` tuples
    """
    if images is not None:
        yield from _iter_images(images)
    if rpms is not None:
        yield from _iter_rpms(rpms)
    if extra_files is not None:
        yield from _iter_extra_files(extra_files)
    if modules is not None:
        yield from _iter_modules(modules)
    if composeinfo is not None:
        yield from _iter_composeinfo(composeinfo)


def _iter_images(images: object) -> Iterator[LocationEntry]:
    """Yield LocationEntry for each image."""
    for variant in images.images:
        for arch in images.images[variant]:
            for image in images.images[variant][arch]:

                def _setter(loc, _img=image):
                    # Preserve existing size/checksum if the new Location
                    # doesn't provide them (e.g. upgrade without compute_checksums).
                    if loc.size is None and _img.size is not None:
                        loc = Location(
                            url=loc.url,
                            size=_img.size,
                            checksum=loc.checksum,
                            local_path=loc.local_path,
                        )
                    if loc.checksum is None and _img.checksums:
                        if "sha256" in _img.checksums:
                            checksum = f"sha256:{_img.checksums['sha256']}"
                        else:
                            algo = next(iter(_img.checksums))
                            checksum = f"{algo}:{_img.checksums[algo]}"
                        loc = Location(
                            url=loc.url,
                            size=loc.size,
                            checksum=checksum,
                            local_path=loc.local_path,
                        )
                    _img.location = loc

                yield LocationEntry(
                    MetadataType.IMAGE,
                    variant,
                    arch,
                    image.path,
                    image._location,
                    _setter,
                )


def _iter_rpms(rpms: object) -> Iterator[LocationEntry]:
    """Yield LocationEntry for each RPM."""
    for variant in rpms.rpms:
        for arch in rpms.rpms[variant]:
            for srpm_nevra in rpms.rpms[variant][arch]:
                for rpm_nevra, rpm_data in rpms.rpms[variant][arch][srpm_nevra].items():

                    def _setter(loc, _data=rpm_data):
                        _data["_location"] = loc

                    yield LocationEntry(
                        MetadataType.RPM,
                        variant,
                        arch,
                        rpm_data["path"],
                        rpm_data.get("_location"),
                        _setter,
                    )


def _iter_extra_files(extra_files: object) -> Iterator[LocationEntry]:
    """Yield LocationEntry for each extra file."""
    for variant in extra_files.extra_files:
        for arch in extra_files.extra_files[variant]:
            for entry in extra_files.extra_files[variant][arch]:

                def _setter(loc, _entry=entry):
                    _entry["_location"] = loc

                yield LocationEntry(
                    MetadataType.EXTRA_FILE,
                    variant,
                    arch,
                    entry["file"],
                    entry.get("_location"),
                    _setter,
                )


def _iter_modules(modules: object) -> Iterator[LocationEntry]:
    """Yield LocationEntry for each module."""
    from productmd.modules import Modules

    for variant in modules.modules:
        for arch in modules.modules[variant]:
            for uid, entry in modules.modules[variant][arch].items():
                path = Modules._get_modulemd_path(entry)

                def _setter(loc, _entry=entry):
                    _entry["_location"] = loc

                yield LocationEntry(
                    MetadataType.MODULE,
                    variant,
                    arch,
                    path,
                    entry.get("_location"),
                    _setter,
                )


def _iter_variant_paths(variant: object) -> Iterator[LocationEntry]:
    """Yield LocationEntry for each path in a variant (recursive)."""
    paths = variant.paths
    for field_name in paths._fields:
        field = getattr(paths, field_name)
        for arch, path in field.items():
            loc = paths.get_location(field_name, arch)

            def _setter(loc, _paths=paths, _field=field_name, _arch=arch):
                _paths.set_location(_field, _arch, loc)

            yield LocationEntry(
                MetadataType.VARIANT_PATH,
                variant.uid,
                arch,
                path,
                loc,
                _setter,
                field_name,
            )
    # Recurse into child variants
    for child_variant in variant.variants.values():
        yield from _iter_variant_paths(child_variant)


def _iter_composeinfo(composeinfo: object) -> Iterator[LocationEntry]:
    """Yield LocationEntry for all variant paths in compose info."""
    for variant_id in composeinfo.variants:
        variant = composeinfo.variants[variant_id]
        yield from _iter_variant_paths(variant)


def _copy_metadata(obj: object) -> object:
    """Create a deep copy of a metadata object via serialize/deserialize.

    Always serializes as v1.2 to avoid triggering v2.0 strict Location
    requirements — the copy is a transient intermediate, not a format
    conversion.  The caller (upgrade_to_v2 / downgrade_to_v1) will set
    Locations and output_version on the copy afterwards.

    .. note::

       Because the copy round-trips through v1.2, any v2.0-only data
       (e.g. ``contents`` / ``FileEntry`` on OCI Locations) is not
       preserved.  This is intentional — ``upgrade_to_v2`` is designed
       for v1.x → v2.0 conversion, not for re-processing existing
       v2.0 metadata.

    :param obj: Metadata object to copy
    :return: New metadata object with identical data
    """
    data = {}
    # Always serialize as v1.2 for the copy round-trip.  v2.0 serialization
    # requires every path to have a Location, which may not be true on the
    # source object.  The v1.2 path preserves all data without that
    # requirement.
    obj.serialize(data, force_version=VERSION_1_2)
    new_obj = type(obj)()
    new_obj.deserialize(data)
    return new_obj


def _compute_checksum_and_size(file_path: str) -> Tuple[str, int]:
    """
    Compute SHA-256 checksum and file size.

    Thread-safe — each call creates its own hashlib instance and
    file handle.

    :param file_path: Path to the file
    :return: Tuple of (checksum string, file size in bytes)
    """
    checksum = compute_checksum(file_path, "sha256")
    size = os.path.getsize(file_path)
    return checksum, size


def upgrade_to_v2(
    output_dir: Optional[str] = None,
    images: Optional[object] = None,
    rpms: Optional[object] = None,
    extra_files: Optional[object] = None,
    modules: Optional[object] = None,
    composeinfo: Optional[object] = None,
    base_url: str = "",
    compute_checksums: bool = False,
    compose_path: Optional[str] = None,
    strict_checksums: bool = False,
    url_mapper: Optional[Callable] = None,
    progress_callback: Optional[Callable] = None,
    parallel_checksums: int = 4,
) -> Dict[str, object]:
    """
    Upgrade v1.x metadata to v2.0 format with Location objects.

    Creates new metadata objects (originals are not modified). For each
    artifact, constructs a Location with a remote URL derived from
    *base_url* + *local_path*, or from the *url_mapper* callable.

    :param output_dir: Directory to write v2.0 metadata files (optional)
    :param images: :class:`~productmd.images.Images` instance to upgrade
    :param rpms: :class:`~productmd.rpms.Rpms` instance to upgrade
    :param extra_files: :class:`~productmd.extra_files.ExtraFiles` instance to upgrade
    :param modules: :class:`~productmd.modules.Modules` instance to upgrade
    :param composeinfo: :class:`~productmd.composeinfo.ComposeInfo` instance to upgrade
    :param base_url: Base URL prefix for constructing remote URLs
    :param compute_checksums: Compute SHA-256 checksums and sizes from local files
    :param compose_path: Path to local compose root (required when *compute_checksums* is True)
    :param strict_checksums: Raise :class:`FileNotFoundError` instead of warning
        when a file cannot be found for checksum computation
    :param url_mapper: Custom callable ``(local_path, variant, arch, metadata_type) -> url``.
        When provided, *base_url* is ignored.
    :param progress_callback: Optional callable ``(processed, total, path, checksum)``
        invoked after each artifact is processed.  *checksum* is the
        computed checksum string or ``None``.  Useful for displaying
        progress during checksum computation on large composes.
    :param parallel_checksums: Number of threads for parallel checksum
        computation (default: 4).  Only used when *compute_checksums*
        is True.  Set to 1 for sequential computation.
    :return: Dict mapping module names to upgraded metadata objects
    :rtype: dict
    :raises ValueError: If *compute_checksums* is True but *compose_path* is not provided
    :raises FileNotFoundError: If *strict_checksums* is True and a file is missing
    """
    if compute_checksums and compose_path is None:
        raise ValueError("compose_path is required when compute_checksums is True")

    result = {}

    # Deep-copy each provided metadata object
    new_images = _copy_metadata(images) if images is not None else None
    new_rpms = _copy_metadata(rpms) if rpms is not None else None
    new_extra_files = _copy_metadata(extra_files) if extra_files is not None else None
    new_modules = _copy_metadata(modules) if modules is not None else None
    new_composeinfo = _copy_metadata(composeinfo) if composeinfo is not None else None

    # Normalize base_url to ensure it ends with a slash so that
    # base_url + path produces a valid URL.
    if base_url and not base_url.endswith("/"):
        base_url += "/"

    # Collect all entries upfront so we know the total count for
    # progress reporting.
    entries = list(
        iter_all_locations(
            images=new_images,
            rpms=new_rpms,
            extra_files=new_extra_files,
            modules=new_modules,
            composeinfo=new_composeinfo,
        )
    )
    total = len(entries)

    # Process entries in batches when parallel checksums are enabled.
    # Each batch computes checksums in parallel, then builds Location
    # objects and fires the progress callback sequentially.  This gives
    # the user periodic progress output instead of one long pause.
    #
    # When checksums are not requested or parallel_checksums <= 1,
    # batch_size is set to total so everything runs in one pass.
    use_parallel = compute_checksums and compose_path is not None and parallel_checksums > 1
    batch_size = parallel_checksums if use_parallel else max(total, 1)

    # Validate missing files upfront before starting any threads.
    # This ensures strict_checksums errors are raised early.
    if compute_checksums and compose_path is not None:
        for entry in entries:
            if entry.metadata_type == MetadataType.VARIANT_PATH:
                continue
            file_path = os.path.join(compose_path, entry.path)
            if not os.path.isfile(file_path):
                if strict_checksums:
                    raise FileNotFoundError(f"Cannot compute checksum: file not found: {file_path}")
                else:
                    warnings.warn(f"Cannot compute checksum: file not found: {file_path}", stacklevel=2)

    # Use a single executor for the entire operation to avoid repeated
    # thread creation overhead on large composes.
    executor = ThreadPoolExecutor(max_workers=parallel_checksums) if use_parallel else None

    try:
        for group_start in range(0, total, batch_size):
            group = entries[group_start : group_start + batch_size]
            group_checksums = {}

            # Compute checksums for this batch
            if compute_checksums and compose_path is not None:
                tasks_in_group = []
                for offset, entry in enumerate(group):
                    idx = group_start + offset
                    if entry.metadata_type == MetadataType.VARIANT_PATH:
                        continue
                    file_path = os.path.join(compose_path, entry.path)
                    if os.path.isfile(file_path):
                        tasks_in_group.append((idx, file_path))

                if executor is not None and len(tasks_in_group) > 1:
                    future_to_index = {}
                    for idx, file_path in tasks_in_group:
                        future = executor.submit(_compute_checksum_and_size, file_path)
                        future_to_index[future] = idx
                    for future in as_completed(future_to_index):
                        group_checksums[future_to_index[future]] = future.result()
                else:
                    for idx, file_path in tasks_in_group:
                        group_checksums[idx] = _compute_checksum_and_size(file_path)

            # Build Locations and fire progress for this batch (sequential, in order)
            for offset, entry in enumerate(group):
                idx = group_start + offset
                processed = idx + 1

                # Build URL
                if url_mapper is not None:
                    url = url_mapper(entry.path, entry.variant, entry.arch, entry.metadata_type)
                else:
                    url = base_url + entry.path

                # Preserve existing size/checksum from the current location
                size = entry.location.size if entry.location is not None else None
                checksum = entry.location.checksum if entry.location is not None else None

                # Apply computed checksum from this batch
                if idx in group_checksums:
                    checksum, size = group_checksums[idx]

                loc = Location(
                    url=url,
                    size=size,
                    checksum=checksum,
                    local_path=entry.path,
                )
                entry.set_location(loc)

                if progress_callback is not None:
                    progress_callback(processed, total, entry.path, checksum)
    finally:
        if executor is not None:
            executor.shutdown(wait=False)

    # Set output version and collect results
    if new_images is not None:
        new_images.output_version = VERSION_2_0
        result["images"] = new_images
    if new_rpms is not None:
        new_rpms.output_version = VERSION_2_0
        result["rpms"] = new_rpms
    if new_extra_files is not None:
        new_extra_files.output_version = VERSION_2_0
        result["extra_files"] = new_extra_files
    if new_modules is not None:
        new_modules.output_version = VERSION_2_0
        result["modules"] = new_modules
    if new_composeinfo is not None:
        new_composeinfo.output_version = VERSION_2_0
        result["composeinfo"] = new_composeinfo

    # Write output files if requested
    if output_dir is not None:
        _write_metadata(output_dir, result)

    return result


def downgrade_to_v1(
    output_dir: Optional[str] = None,
    images: Optional[object] = None,
    rpms: Optional[object] = None,
    extra_files: Optional[object] = None,
    modules: Optional[object] = None,
    composeinfo: Optional[object] = None,
) -> Dict[str, object]:
    """
    Downgrade v2.0 metadata to v1.2 format (metadata only, no downloads).

    Creates new metadata objects (originals are not modified). Location
    objects are converted to plain path strings using ``local_path``.

    :param output_dir: Directory to write v1.2 metadata files (optional)
    :param images: :class:`~productmd.images.Images` instance to downgrade
    :param rpms: :class:`~productmd.rpms.Rpms` instance to downgrade
    :param extra_files: :class:`~productmd.extra_files.ExtraFiles` instance to downgrade
    :param modules: :class:`~productmd.modules.Modules` instance to downgrade
    :param composeinfo: :class:`~productmd.composeinfo.ComposeInfo` instance to downgrade
    :return: Dict mapping module names to downgraded metadata objects
    :rtype: dict
    """
    result = {}

    # Deep-copy and set output version to v1.2
    if images is not None:
        new_images = _copy_metadata(images)
        new_images.output_version = VERSION_1_2
        result["images"] = new_images
    if rpms is not None:
        new_rpms = _copy_metadata(rpms)
        new_rpms.output_version = VERSION_1_2
        result["rpms"] = new_rpms
    if extra_files is not None:
        new_extra_files = _copy_metadata(extra_files)
        new_extra_files.output_version = VERSION_1_2
        result["extra_files"] = new_extra_files
    if modules is not None:
        new_modules = _copy_metadata(modules)
        new_modules.output_version = VERSION_1_2
        result["modules"] = new_modules
    if composeinfo is not None:
        new_composeinfo = _copy_metadata(composeinfo)
        new_composeinfo.output_version = VERSION_1_2
        result["composeinfo"] = new_composeinfo

    # Write output files if requested
    if output_dir is not None:
        _write_metadata(output_dir, result)

    return result


_MODULE_FILENAMES = {
    "images": "images.json",
    "rpms": "rpms.json",
    "extra_files": "extra_files.json",
    "modules": "modules.json",
    "composeinfo": "composeinfo.json",
}


def _write_metadata(output_dir: str, result: Dict[str, object]) -> None:
    """Write metadata objects to JSON files in the output directory."""
    os.makedirs(output_dir, exist_ok=True)
    for key, obj in result.items():
        filename = _MODULE_FILENAMES.get(key)
        if filename is not None:
            obj.dump(os.path.join(output_dir, filename))
