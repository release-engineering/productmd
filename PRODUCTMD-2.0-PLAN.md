# ProductMD 2.0 - Distributed Compose Metadata

## Executive Summary

ProductMD 2.0 introduces support for **distributed composes** where artifacts
(RPMs, images, repositories) can be stored in different locations and
referenced via HTTPS URLs or OCI registry references. The metadata includes
checksums for data integrity verification and supports bidirectional conversion
between v2.0 (distributed) and v1.2 (local) formats.

The implementation is divided into **two phases**:

**Phase 1: Distributed Compose Metadata** - Core metadata format supporting
distributed storage with Location objects, checksums, and localization.

**Phase 2: Supplementary Pipeline Attachments** - OCI registry attachment
mechanism enabling independent pipelines to add supplementary metadata
(e.g., cloud images, container images) without modifying core compose metadata.

---

## Table of Contents

**Phase 1: Distributed Composes**

1. [Core Design Principles](#core-design-principles)
2. [Metadata Schema Changes](#metadata-schema-changes)
3. [Location Object Specification](#location-object-specification)
4. [URL Schemes and Storage Backends](#url-schemes-and-storage-backends)
5. [Checksum Strategy](#checksum-strategy)
6. [Repository Metadata Handling](#repository-metadata-handling)
7. [Extra Files Metadata](#extra-files-metadata)
8. [TreeInfo Compatibility](#treeinfo-compatibility)
9. [Backward Compatibility](#backward-compatibility)
10. [Conversion Tools](#conversion-tools)
11. [Localization Strategy](#localization-strategy)
12. [Implementation Plan](#implementation-plan)
13. [Testing Strategy](#testing-strategy)

**Phase 2: Supplementary Pipeline Attachments**

14. [Supplementary Pipelines Overview](#supplementary-pipelines-overview)
15. [OCI Attachment Mechanism](#oci-attachment-mechanism)
16. [Pipeline Status Tracking](#pipeline-status-tracking)
17. [Pipeline Manifest (Optional)](#pipeline-manifest-optional)
18. [Client Behavior with Attachments](#client-behavior-with-attachments)
19. [Validation Requirements](#validation-requirements)
20. [Phase 2 Implementation Plan](#phase-2-implementation-plan)

---

## 1. Core Design Principles

### 1.1 Goals

- ✅ **Support distributed storage**: Artifacts can be referenced by HTTPS URLs
  or OCI registry references
- ✅ **Ensure data integrity**: All artifacts must have SHA-256 checksums in
  metadata
- ✅ **Maintain backward compatibility**: Can read and write v1.2 metadata
  indefinitely
- ✅ **Enable perfect replication**: v2.0 → v1.2 conversion preserves exact
  filesystem layout
- ✅ **Preserve existing semantics**: No breaking changes to core concepts

### 1.2 Key Requirements

Each artifact (RPM, image, repository) must have:
- A **location** (relative path OR absolute HTTPS URL OR OCI registry reference)
- **SHA-256 checksum** in `"sha256:hash"` format
- **Size** in bytes
- **Local path hint** for preserving v1.2 filesystem layout

---

## 2. Metadata Schema Changes

### 2.1 Affected Metadata Files

All JSON metadata files will support v2.0 format:
- `composeinfo.json` - Compose and variant metadata
- `rpms.json` - RPM package metadata
- `images.json` - Image metadata
- `extra_files.json` - Extra files (EULA, GPG keys, etc.)
- `modules.json` - Module metadata (future)

**Note:** `.treeinfo` files remain at v1.2 format (INI) with no changes.

---

## 3. Location Object Specification

### 3.1 Location Class

```python
class Location(MetadataBase):
    """
    Represents artifact location with integrity information

    Attributes:
        url (str): HTTPS URL, OCI reference, or relative path
        size (int): Size in bytes (total size of OCI image with contents)
        checksum (str): Checksum in "algorithm:hash" format (e.g., "sha256:abc123...")
        local_path (str): Relative path for v1.2 filesystem layout preservation
        contents (list[FileEntry], optional): For OCI images, list of files
                                              contained in the image (as layers)
                                              that are being referenced
    """

class FileEntry(MetadataBase):
    """
    Represents a file within an OCI image location

    Attributes:
        file (str): Relative path of the file within the container
        size (int): File size in bytes
        checksum (str): File checksum in "algorithm:hash" format
        layer_digest (str): OCI layer digest containing this file
    """
```

### 3.2 Location Serialization Format

**v2.0 Format (Simple File):**
```json
{
  "url": "https://cdn.example.com/Packages/bash-5.2.15-3.fc39.x86_64.rpm",
  "size": 1849356,
  "checksum": "sha256:8f3e9d2c1a0b7f6e5d4c3b2a1098fedcba",
  "local_path": "Server/x86_64/os/Packages/b/bash-5.2.15-3.fc39.x86_64.rpm"
}
```

**v2.0 Format (OCI Image with Contents):**
```json
{
  "url": "oci://quay.io/fedora/boot-files:server-39-x86_64@sha256:abc123...",
  "size": 101376000,
  "checksum": "sha256:abc123...",
  "local_path": "Server/x86_64/os/images",
  "contents": [
    {
      "file": "pxeboot/vmlinuz",
      "size": 11534336,
      "checksum": "sha256:def456...",
      "layer_digest": "sha256:def456..."
    },
    {
      "file": "pxeboot/initrd.img",
      "size": 89478656,
      "checksum": "sha256:ghi789...",
      "layer_digest": "sha256:ghi789..."
    },
    {
      "file": "efiboot.img",
      "size": 8388608,
      "checksum": "sha256:jkl012...",
      "layer_digest": "sha256:jkl012..."
    }
  ]
}
```

**v1.2 Compatibility:**
```json
{
  "path": "Server/x86_64/os/Packages/b/bash-5.2.15-3.fc39.x86_64.rpm"
}
```

### 3.3 OCI Images with Contents

The `contents` field enables storing multiple files as layers within a single OCI image. This pattern is useful for:

- **Boot files**: Kernel, initrd, and EFI images for an architecture
- **RPM bundles**: Grouped RPMs for efficient distribution
- **Curated package sets**: Module or addon packages
- **Related artifacts**: Any collection of files logically grouped together

#### 3.3.1 Benefits

1. **Single reference**: One OCI image URL instead of many individual URLs
2. **Efficient storage**: Registry-level deduplication across images
3. **Atomic updates**: All files updated together with one image push
4. **Layer caching**: Individual files can be cached/reused via layer digests
5. **Partial downloads**: Can fetch specific layers when needed

#### 3.3.2 OCI Image Structure

Each file becomes a separate layer in the OCI image:

```
OCI Image: quay.io/fedora/boot-files:server-39-x86_64@sha256:abc123
├── Config (JSON manifest describing contents)
├── Layer 0: sha256:def456... (pxeboot/vmlinuz)
├── Layer 1: sha256:ghi789... (pxeboot/initrd.img)
└── Layer 2: sha256:jkl012... (efiboot.img)
```

The `layer_digest` in each `FileEntry` matches the OCI layer containing that file.

#### 3.3.3 Localization Process

When localizing an OCI image with contents:

1. Pull the OCI image using the image digest
2. For each file in `contents`:
   - Extract the layer matching `layer_digest`
   - Verify file checksum matches
   - Write to `{output_dir}/compose/{local_path}/{file}`
3. Result: Individual files placed in their correct filesystem locations

#### 3.3.4 Use Cases

**Boot Files Example:**
```json
{
  "location": {
    "url": "oci://quay.io/fedora/boot-files:server-39-x86_64@sha256:...",
    "local_path": "Server/x86_64/os/images",
    "contents": [
      {"file": "pxeboot/vmlinuz", "layer_digest": "sha256:..."},
      {"file": "pxeboot/initrd.img", "layer_digest": "sha256:..."}
    ]
  }
}
```

**RPM Bundle Example:**
```json
{
  "location": {
    "url": "oci://quay.io/fedora/rpms:server-39-x86_64-core@sha256:...",
    "local_path": "Server/x86_64/os/Packages",
    "contents": [
      {"file": "b/bash-5.2.15-3.fc39.x86_64.rpm", "layer_digest": "sha256:..."},
      {"file": "c/coreutils-9.1-8.fc39.x86_64.rpm", "layer_digest": "sha256:..."},
      {"file": "g/glibc-2.38-7.fc39.x86_64.rpm", "layer_digest": "sha256:..."}
    ]
  }
}
```

---

## 4. URL Schemes and Storage Backends

### 4.1 Supported URL Schemes

| Scheme | Description | Example | Use Case |
|--------|-------------|---------|----------|
| **https://** | Direct HTTPS URL | `https://cdn.fedoraproject.org/fedora/39/...` | CDN distribution |
| **http://** | HTTP URL (testing only) | `http://internal-mirror.corp/...` | Internal testing |
| **oci://** | OCI registry reference | `oci://quay.io/fedora/rpms:bash@sha256:...` | Container registry storage |
| **Relative** | Local relative path | `Server/x86_64/os/Packages/b/bash-*.rpm` | Local compose |

### 4.2 OCI Registry References

**Format:** `oci://registry.example.com/namespace/image:tag@sha256:digest`

**Requirements:**
- **MUST** include digest (`@sha256:...`) for immutability
- Digest matches the artifact checksum
- Compatible with OCI Artifacts specification

---

## 5. Checksum Strategy

### 5.1 Single Checksum Format

**Decision:** Use only SHA-256 checksums in a self-describing format.

**Format:** `"sha256:hexdigest"`

**Example:** `"sha256:8f3e9d2c1a0b7f6e5d4c3b2a1098fedcba9876543210..."`

### 5.2 Rationale

- **Simplicity**: Single format, no ambiguity
- **Security**: SHA-256 is cryptographically secure
- **Standard**: Matches Docker/OCI image digest format
- **Future-proof**: Algorithm prefix allows evolution (e.g., sha512) without schema changes

---

## 6. Repository Metadata Handling

### 6.1 Repository Location Structure

For YUM/DNF repositories, the Location object represents the repository base URL:

```json
{
  "repository": {
    "x86_64": {
      "url": "https://cdn.fedoraproject.org/fedora/39/Server/x86_64/os/",
      "size": 2847,
      "checksum": "sha256:a1b2c3d4e5f6...",
      "local_path": "Server/x86_64/os"
    }
  }
}
```

### 6.2 Checksum Semantics for Repositories

**Important:** The checksum for a repository Location is the SHA-256 of `repomd.xml` **only**.

**Why this works:**
```
Repository URL: https://cdn.example.com/repos/Server/x86_64/
├── repodata/
│   ├── repomd.xml          ← This file is checksummed in metadata
│   ├── primary.xml.gz      ← Checksummed inside repomd.xml
│   ├── filelists.xml.gz    ← Checksummed inside repomd.xml
│   └── other.xml.gz        ← Checksummed inside repomd.xml
└── Packages/
    └── ...
```

The `repomd.xml` file contains checksums of all other repository metadata files, creating a complete chain of trust.

---

## 7. Extra Files Metadata

### 7.1 Purpose

**Extra files** are additional files that must be included in a compose but are
not RPMs, images, or repository metadata. Common examples include:

- EULA files
- GPG signing keys (e.g., `RPM-GPG-KEY-fedora-39-primary`)
- License documents
- README files
- Custom scripts or tools

These files need to be:
- Stored at specific paths in localized composes
- Referenced by Location objects in distributed composes
- Preserved during round-trip conversions

### 7.2 Extra Files Metadata File

**File:** `extra_files.json`

This new metadata file tracks all extra files included in the compose.

**v2.0 Format:**
```json
{
  "header": {
    "version": "2.0",
    "type": "productmd.extra_files"
  },
  "payload": {
    "compose": {
      "id": "Fedora-39-20231201.0",
      "type": "production",
      "date": "20231201",
      "respin": 0
    },
    "extra_files": {
      "Server": {
        "x86_64": [
          {
            "file": "EULA",
            "location": {
              "url": "https://cdn.fedoraproject.org/fedora/39/Server/x86_64/os/EULA",
              "size": 18385,
              "checksum": "sha256:7c8b9a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b",
              "local_path": "Server/x86_64/os/EULA"
            }
          },
          {
            "file": "RPM-GPG-KEY-fedora-39-primary",
            "location": {
              "url": "https://cdn.fedoraproject.org/fedora/39/Server/x86_64/os/RPM-GPG-KEY-fedora-39-primary",
              "size": 3112,
              "checksum": "sha256:a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789a",
              "local_path": "Server/x86_64/os/RPM-GPG-KEY-fedora-39-primary"
            }
          }
        ]
      }
    }
  }
}
```

**v1.2 Format (for backward compatibility):**
```json
{
  "header": {
    "version": "1.2",
    "type": "productmd.extra_files"
  },
  "payload": {
    "compose": {
      "id": "Fedora-39-20231201.0",
      "type": "production",
      "date": "20231201",
      "respin": 0
    },
    "extra_files": {
      "Server": {
        "x86_64": [
          {
            "file": "EULA",
            "path": "Server/x86_64/os/EULA",
            "size": 18385,
            "checksums": {
              "sha256": "7c8b9a6f5e4d3c2b1a0f9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b"
            }
          }
        ]
      }
    }
  }
}
```

### 7.3 ExtraFiles Class

```python
class ExtraFile(MetadataBase):
    """
    Represents an extra file in the compose

    Attributes:
        file (str): Base filename
        location (Location): Location object with URL, checksum, size, and local_path
        variant (str): Variant ID this file belongs to
        arch (str): Architecture
    """
```

### 7.5 Boot Files

**Boot files** are architecture-specific files required for network booting and
installation. These files are typically stored alongside the repository
metadata in the variant/arch directory structure.

#### 7.5.1 Common Boot Files

Typical PXE boot files by architecture:

**x86_64:**
- `images/pxeboot/vmlinuz` - Linux kernel
- `images/pxeboot/initrd.img` - Initial ramdisk
- `images/efiboot.img` - EFI boot image
- `images/boot.iso` - Bootable ISO

**aarch64:**
- `images/pxeboot/vmlinuz` - Linux kernel
- `images/pxeboot/initrd.img` - Initial ramdisk
- `images/efiboot.img` - EFI boot image

**ppc64le:**
- `ppc/ppc64/vmlinuz` - Linux kernel
- `ppc/ppc64/initrd.img` - Initial ramdisk

**s390x:**
- `images/kernel.img` - Linux kernel
- `images/initrd.img` - Initial ramdisk
- `images/generic.prm` - Parameter file

#### 7.5.2 Storage Options

Boot files can be stored in two ways:

**Option 1: Individual Files** (suitable for HTTPS storage):

```json
{
  "extra_files": {
    "Server": {
      "x86_64": [
        {
          "file": "images/pxeboot/vmlinuz",
          "location": {
            "url": "https://cdn.fedoraproject.org/fedora/39/Server/x86_64/os/images/pxeboot/vmlinuz",
            "size": 11534336,
            "checksum": "sha256:8a9b7c6d...",
            "local_path": "Server/x86_64/os/images/pxeboot/vmlinuz"
          }
        }
      ]
    }
  }
}
```

**Option 2: OCI Image with Contents** (recommended for OCI registries):

```json
{
  "extra_files": {
    "Server": {
      "x86_64": [
        {
          "file": "boot-files",
          "location": {
            "url": "oci://quay.io/fedora/boot-files:server-39-x86_64@sha256:abc123...",
            "size": 101376000,
            "checksum": "sha256:abc123...",
            "local_path": "Server/x86_64/os/images",
            "contents": [
              {
                "file": "pxeboot/vmlinuz",
                "size": 11534336,
                "checksum": "sha256:def456...",
                "layer_digest": "sha256:def456..."
              },
              {
                "file": "pxeboot/initrd.img",
                "size": 89478656,
                "checksum": "sha256:ghi789...",
                "layer_digest": "sha256:ghi789..."
              },
              {
                "file": "efiboot.img",
                "size": 8388608,
                "checksum": "sha256:jkl012...",
                "layer_digest": "sha256:jkl012..."
              }
            ]
          }
        }
      ]
    }
  }
}
```

Option 2 is preferred when using OCI registries because:
- Single artifact to push/pull per architecture
- All boot files updated atomically
- Efficient layer-based storage and caching
- Built-in registry deduplication

### 7.6 Localization Behavior

When localizing a distributed compose, extra files (including boot files)
are handled the same as other artifacts:

1. Download from `location.url`
2. Save to `{output_dir}/compose/{location.local_path}`
3. Verify checksum matches `location.checksum`
4. Update metadata to v1.2 format with local paths

**Example:**
```bash
$ productmd-localize \
    --input https://cdn.example.com/metadata/composeinfo.json \
    --output /mnt/local-compose

# Results in:
# /mnt/local-compose/compose/Server/x86_64/os/EULA
# /mnt/local-compose/compose/Server/x86_64/os/RPM-GPG-KEY-fedora-39-primary
# /mnt/local-compose/compose/Server/x86_64/os/images/pxeboot/vmlinuz
# /mnt/local-compose/compose/Server/x86_64/os/images/pxeboot/initrd.img
# /mnt/local-compose/compose/Server/x86_64/os/images/efiboot.img
```

---

## 8. TreeInfo Compatibility

### 8.1 Design Decision

**TreeInfo files (.treeinfo) remain at v1.2 format with NO changes.**

**Rationale:**
- `.treeinfo` is used for local media (ISOs, mounted filesystems)
- Changing format would break compatibility with installers for no benefit

### 8.2 Creating TreeInfo from Distributed Compose

To create `.treeinfo` files from a v2.0 distributed compose:

```bash
# Step 1: Localize the compose
$ productmd-localize \
    --input https://cdn.example.com/metadata/composeinfo.json \
    --output /mnt/local-compose

# Step 2: Generate .treeinfo (automatically done by localize)
# Result: /mnt/local-compose/compose/Server/x86_64/.treeinfo
```

---

## 9. Backward Compatibility

### 9.1 Version Selection

```python
# Default behavior: auto-detect on read, write as v2.0
compose = Compose("/path/to/compose")
compose.info.dump("output.json")  # Writes v2.0 by default

# Explicit version control
compose.info.header.version = "1.2"
compose.info.dump("output.json")  # Writes v1.2

# Or use parameter
compose.info.dump("output.json", force_version="1.2")
```

---

## 10. Conversion Tools

### 10.1 Upgrade: v1.2 → v2.0

```bash
$ productmd-upgrade \
    --input /path/to/v1.2-compose \
    --output /path/to/v2.0-metadata \
    --base-url https://cdn.example.com/compose/ \
    --compute-checksums
```

**Process:**
1. Load v1.2 metadata from local compose
2. Create `Location` objects for each artifact
3. Set `url` to remote URL (`base_url` + `local_path`)
4. Set `local_path` to preserve original v1.2 structure
5. Compute SHA-256 checksums from local files
6. Write v2.0 metadata files

### 10.2 Downgrade: v2.0 → v1.2

```bash
$ productmd-downgrade \
    --input https://cdn.example.com/metadata/composeinfo.json \
    --output /path/to/v1.2-compose \
    --download-artifacts
```

**Process:**
1. Load v2.0 metadata from remote URL
2. Check if all locations are local OR have `local_path` hints
3. Download remote artifacts if `--download-artifacts` specified
4. Convert Location objects to simple path strings using `local_path`
5. Write v1.2 metadata files

**Validation:**
- Fails if remote URLs present and `--download-artifacts` not specified
- Fails if remote locations missing `local_path` hints

### 10.3 Custom URL Mapping

Advanced usage with custom URL mapping function:

```python
def custom_url_mapper(local_path, variant, arch, artifact_type):
    """Map local paths to custom remote URLs"""
    if artifact_type == "rpm":
        return f"oci://quay.io/fedora/rpms:{os.path.basename(local_path)}@sha256:..."
    elif artifact_type == "image":
        return f"https://download.fedoraproject.org/{local_path}"
    else:
        return f"https://cdn.fedoraproject.org/{local_path}"

upgrade_to_v2("/path/to/compose", "/tmp/v2", url_mapper=custom_url_mapper)
```

---

## 11. Localization Strategy

### 11.1 Purpose

**Localization** is the process of downloading a distributed v2.0 compose to
local storage, recreating the exact v1.2 filesystem layout.

### 11.2 How It Works

The `local_path` field in each Location object specifies where to place the
artifact in the local filesystem:

```json
{
  "location": {
    "url": "https://cdn.example.com/bash-5.2.15-3.fc39.x86_64.rpm",
    "local_path": "Server/x86_64/os/Packages/b/bash-5.2.15-3.fc39.x86_64.rpm"
  }
}
```

When localizing:
1. Create directory: `{output_dir}/compose/Server/x86_64/os/Packages/b/`
2. Download from: `https://cdn.example.com/bash-5.2.15-3.fc39.x86_64.rpm`
3. Save to: `{output_dir}/compose/Server/x86_64/os/Packages/b/bash-5.2.15-3.fc39.x86_64.rpm`
4. Verify: SHA-256 checksum matches `location.checksum`

### 11.3 Standard Compose Layout

The localized compose recreates the standard v1.2 structure:

```
output_dir/
└── compose/
    ├── metadata/
    │   ├── composeinfo.json      # v1.2 format
    │   ├── rpms.json             # v1.2 format
    │   └── images.json           # v1.2 format
    ├── Server/
    │   ├── x86_64/
    │   │   ├── os/                       # Repository root
    │   │   │   ├── .treeinfo             # Generated
    │   │   │   ├── repodata/
    │   │   │   │   └── repomd.xml
    │   │   │   └── Packages/
    │   │   │       └── b/
    │   │   │           └── bash-5.2.15-3.fc39.x86_64.rpm
    │   │   └── iso/
    │   │       └── Fedora-Server-dvd-x86_64-39.iso
    │   └── aarch64/
    │       └── ...
    └── Workstation/
        └── ...
```

### 11.4 Localize Command

```bash
$ productmd-localize \
    --input https://cdn.example.com/metadata/composeinfo.json \
    --output /mnt/local-compose \
    --parallel-downloads 8 \
    --verify-checksums \
    --skip-existing
```

**Options:**
- `--input`: URL to v2.0 composeinfo.json
- `--output`: Local directory to create compose
- `--parallel-downloads`: Number of concurrent downloads (default: 4)
- `--verify-checksums`: Verify SHA-256 after download (default: true)
- `--skip-existing`: Skip files that exist and have correct checksum

**Process:**
1. Load v2.0 metadata from remote URL
2. Collect all remote artifacts (check `location.is_remote`)
3. Determine local paths using `location.get_localized_path()`
4. Download artifacts in parallel (with progress bar)
5. Verify checksums after each download
6. Update metadata to use local paths (set `location.url = location.local_path`)
7. Write v1.2 metadata files
8. Generate `.treeinfo` files for each variant

---

## 12. Implementation Plan

### Phase 1: Core Infrastructure

**Deliverables:**
- [ ] Update `VERSION` to `(2, 0)` in `productmd/common.py`
- [ ] Implement `Location` class with full validation
- [ ] Implement `FileEntry` class for OCI image contents
- [ ] Add checksum computation utilities (`compute_checksum_file`)
- [ ] Add URL scheme detection (`is_remote_url`, `is_oci_url`)
- [ ] Add OCI image layer extraction utilities
- [ ] Write unit tests for `Location` and `FileEntry` classes

### Phase 2: Metadata Classes

**Deliverables:**
- [ ] Update `VariantPaths` to use Location objects
- [ ] Update `Rpms.add()` to accept Location objects
- [ ] Update `Image` class to use `location` attribute
- [ ] Implement `ExtraFiles` class with `add()` method
- [ ] Implement v2.0 serialization for all metadata classes
- [ ] Implement v2.0 deserialization for all metadata classes
- [ ] Support v1.2 serialization/deserialization (backward compat)
- [ ] Write unit tests for each metadata class

### Phase 3: Conversion Utilities

**Deliverables:**
- [ ] Implement `upgrade_to_v2()` function
- [ ] Implement `downgrade_to_v1()` function
- [ ] Implement `iter_all_locations()` generator
- [ ] Write conversion tests (round-trip validation)

### Phase 4: Localization Tool

**Deliverables:**
- [ ] Implement `localize_compose()` function
- [ ] Implement parallel download with progress tracking
- [ ] Implement OCI registry download support (using skopeo/oras)
- [ ] Implement OCI image layer extraction for `contents` field
- [ ] Implement HTTPS download with retry logic
- [ ] Implement checksum verification
- [ ] Write integration tests

### Phase 5: CLI Tools

**Deliverables:**
- [ ] Create `productmd-upgrade` command
- [ ] Create `productmd-downgrade` command
- [ ] Create `productmd-localize` command
- [ ] Create `productmd-verify` command
- [ ] Add man pages and help documentation

### Phase 6: Documentation

**Deliverables:**
- [ ] Write `doc/productmd-2.0.rst` - Complete format specification
- [ ] Write `doc/migration-guide.rst` - v1.2 → v2.0 migration
- [ ] Write `doc/distributed-composes.rst` - Use cases and patterns
- [ ] Update existing docs: `doc/composeinfo.rst`, `doc/rpms.rst`, etc.
- [ ] Add code examples and tutorials

### Phase 7: Testing & Validation

**Deliverables:**
- [ ] Write comprehensive test suite (>90% coverage)
- [ ] Test with real Fedora/RHEL composes
- [ ] Performance testing with large composes
- [ ] Integration testing with existing tools
- [ ] Create test fixtures for v2.0 metadata

---

## 13. Testing Strategy

### 13.1 Unit Tests

All new code should be covered by unit tests.

### 13.2 Conversion Tests

* Testing upgrade from v1.2 to v2.0
* Testing downgrade from v2.0 to v1.2 works when all files are local
* Testing downgrade from v2.0 to v1.2 fails when some files are remote
* Testing roundtrip v1.2 → v2.0 → v1.2 preserves structure

### 13.3 Integration Tests

* Test localizing compose with HTTPS URLs (this would use a test HTTP server)
* Test checksum verification detects corruption

### 13.4 Performance Tests

* Test performance with a large compose (10k+ RPMs)

---

## Appendix A: Example Metadata Files

### A.1 ComposeInfo v2.0

```json
{
  "header": {
    "version": "2.0",
    "type": "productmd.composeinfo"
  },
  "payload": {
    "compose": {
      "id": "Fedora-39-20231201.0",
      "type": "production",
      "date": "20231201",
      "respin": 0
    },
    "release": {
      "name": "Fedora",
      "short": "fedora",
      "version": "39",
      "type": "ga",
      "internal": false
    },
    "variants": {
      "Server": {
        "id": "Server",
        "uid": "Server",
        "name": "Server",
        "type": "variant",
        "arches": ["x86_64", "aarch64"],
        "paths": {
          "repository": {
            "x86_64": {
              "url": "https://cdn.fedoraproject.org/fedora/39/Server/x86_64/os/",
              "size": 2847,
              "checksum": "sha256:a1b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef0123456789a",
              "local_path": "Server/x86_64/os"
            },
            "aarch64": {
              "url": "oci://quay.io/fedora/repos:server-39-aarch64@sha256:f6e5d4c3b2a19876543210fedcba9876543210fedcba9876543210fedcba987",
              "size": 2891,
              "checksum": "sha256:f6e5d4c3b2a19876543210fedcba9876543210fedcba9876543210fedcba987",
              "local_path": "Server/aarch64/os"
            }
          },
          "packages": {
            "x86_64": {
              "url": "https://cdn.fedoraproject.org/fedora/39/Server/x86_64/os/Packages/",
              "local_path": "Server/x86_64/os/Packages"
            }
          }
        }
      }
    }
  }
}
```

### A.2 RPMs v2.0

```json
{
  "header": {
    "version": "2.0",
    "type": "productmd.rpms"
  },
  "payload": {
    "compose": {
      "id": "Fedora-39-20231201.0",
      "type": "production",
      "date": "20231201",
      "respin": 0
    },
    "rpms": {
      "Server": {
        "x86_64": {
          "bash-0:5.2.15-3.fc39.src": {
            "bash-0:5.2.15-3.fc39.x86_64": {
              "location": {
                "url": "https://cdn.fedoraproject.org/fedora/39/Server/x86_64/os/Packages/b/bash-5.2.15-3.fc39.x86_64.rpm",
                "size": 1849356,
                "checksum": "sha256:8f3e9d2c1a0b7f6e5d4c3b2a1098fedcba9876543210fedcba9876543210fedc",
                "local_path": "Server/x86_64/os/Packages/b/bash-5.2.15-3.fc39.x86_64.rpm"
              },
              "sigkey": "e99d6ad1",
              "category": "binary"
            },
            "bash-doc-0:5.2.15-3.fc39.noarch": {
              "location": {
                "url": "oci://quay.io/fedora/rpms:bash-doc-5.2.15-3.fc39@sha256:1a0b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef012345678",
                "size": 2103456,
                "checksum": "sha256:1a0b2c3d4e5f6789abcdef0123456789abcdef0123456789abcdef012345678",
                "local_path": "Server/x86_64/os/Packages/b/bash-doc-5.2.15-3.fc39.noarch.rpm"
              },
              "sigkey": "e99d6ad1",
              "category": "binary"
            }
          }
        }
      }
    }
  }
}
```

### A.3 Images v2.0

```json
{
  "header": {
    "version": "2.0",
    "type": "productmd.images"
  },
  "payload": {
    "compose": {
      "id": "Fedora-39-20231201.0",
      "type": "production",
      "date": "20231201",
      "respin": 0
    },
    "images": {
      "Server": {
        "x86_64": [
          {
            "location": {
              "url": "https://cdn.fedoraproject.org/fedora/39/Server/x86_64/iso/Fedora-Server-dvd-x86_64-39.iso",
              "size": 2147483648,
              "checksum": "sha256:9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d",
              "local_path": "Server/x86_64/iso/Fedora-Server-dvd-x86_64-39.iso"
            },
            "mtime": 1701388800,
            "volume_id": "Fedora-S-dvd-x86_64-39",
            "type": "dvd",
            "format": "iso",
            "arch": "x86_64",
            "disc_number": 1,
            "disc_count": 1,
            "implant_md5": "1a2b3c4d5e6f7890abcdef0123456789",
            "bootable": true,
            "subvariant": "Server",
            "unified": false,
            "additional_variants": []
          },
          {
            "location": {
              "url": "oci://quay.io/fedora/server:39@sha256:5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4",
              "size": 536870912,
              "checksum": "sha256:5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a0f9e8d7c6b5a4",
              "local_path": "Server/x86_64/images/server-container-39.tar"
            },
            "mtime": 1701388800,
            "type": "container",
            "format": "ociarchive",
            "arch": "x86_64",
            "disc_number": 1,
            "disc_count": 1,
            "bootable": false,
            "subvariant": "Server",
            "unified": false,
            "additional_variants": []
          }
        ]
      }
    }
  }
}
```

---

## Appendix B: CLI Tool Usage Examples

### B.1 Upgrade Compose

```bash
# Basic upgrade
$ productmd-upgrade \
    --input /mnt/fedora-39-compose \
    --output /tmp/fedora-39-v2 \
    --base-url https://cdn.fedoraproject.org/fedora/39/

# Upgrade with custom URL mapping
$ productmd-upgrade \
    --input /mnt/rhel-9-compose \
    --output /tmp/rhel-9-v2 \
    --url-map config/url-mapping.json \
    --compute-checksums
```

### B.2 Localize Compose

```bash
# Download distributed compose
$ productmd-localize \
    --input https://cdn.fedoraproject.org/fedora/39/metadata/composeinfo.json \
    --output /mnt/fedora-39-local \
    --parallel-downloads 8

# Resume interrupted download
$ productmd-localize \
    --input https://cdn.fedoraproject.org/fedora/39/metadata/composeinfo.json \
    --output /mnt/fedora-39-local \
    --skip-existing
```

### B.3 Verify Compose

```bash
# Verify integrity of distributed compose
$ productmd-verify \
    --compose https://cdn.fedoraproject.org/fedora/39/metadata/composeinfo.json \
    --report verify-report.json

# Verify local compose
$ productmd-verify \
    --compose /mnt/fedora-39-local \
    --quick  # Only verify metadata, not all artifacts
```

### B.4 Downgrade Compose

```bash
# Downgrade to v1.2 (fails if remote)
$ productmd-downgrade \
    --input https://cdn.fedoraproject.org/fedora/39/metadata/composeinfo.json \
    --output /tmp/fedora-39-v1

# Downgrade with download
$ productmd-downgrade \
    --input https://cdn.fedoraproject.org/fedora/39/metadata/composeinfo.json \
    --output /mnt/fedora-39-v1 \
    --download-artifacts
```

---

# PHASE 2: SUPPLEMENTARY PIPELINE ATTACHMENTS

## 14. Supplementary Pipelines Overview

### 14.1 Problem Statement

Compose creation can involve multiple independent pipelines:

1. **Core pipeline**: Creates essential artifacts (RPM repositories, installer, ISO images)
   - Always required
   - Produces the "main" metadata (composeinfo.json, rpms.json, images.json, etc.)
   - Must complete successfully for a valid compose

2. **Supplementary pipelines**: Create additional artifacts (cloud images,
   container images, live media, etc.)
   - Optional or required depending on product
   - Run after core completes (may depend on core artifacts)
   - Should not block core publication if they fail

### 14.2 Design Goals

- **Decoupled pipelines**: Core and supplementary pipelines don't directly coordinate
- **Immutable core metadata**: Core metadata never changes after publication
- **Failure isolation**: Supplementary pipeline failures don't invalidate core
- **Progressive availability**: Core artifacts available immediately, supplementary added later
- **Completion tracking**: Clients can determine when all expected pipelines have finished

### 14.3 Architecture

```
Core Pipeline
  ├── Produces: composeinfo.json, rpms.json, images.json, extra_files.json
  ├── Pushes to: oci://registry.io/fedora/compose:39-20231201.0
  └── Core manifest is IMMUTABLE after this point

Supplementary Pipelines (run after core)
  ├── Cloud Images Pipeline
  │   ├── Attaches: cloud-images.json (application/vnd.productmd.images+json)
  │   └── Attaches: pipeline status (application/vnd.productmd.pipeline-status+json)
  │
  └── Container Images Pipeline
      ├── Attaches: container-images.json (application/vnd.productmd.images+json)
      └── Attaches: pipeline status (application/vnd.productmd.pipeline-status+json)

Client Library
  └── Discovers and merges all attachments → Unified view
```

---

## 15. OCI Attachment Mechanism

### 15.1 OCI Referrers API

Supplementary pipelines use the OCI referrers API (via `oras attach`) to attach
metadata to the core manifest without modifying it.

**Core manifest:**
```
oci://quay.io/fedora/compose:39-20231201.0@sha256:abc123...
├── composeinfo.json
├── rpms.json
├── images.json
└── extra_files.json
```

**Attachments (via OCI referrers):**
```
oci://quay.io/fedora/compose@sha256:abc123...
├── [referrer 1] cloud-images.json (artifact type: application/vnd.productmd.images+json)
├── [referrer 2] cloud-status-v1.json (artifact type: application/vnd.productmd.pipeline-status+json)
├── [referrer 3] cloud-status-v2.json (artifact type: application/vnd.productmd.pipeline-status+json)
└── [referrer 4] container-images.json (artifact type: application/vnd.productmd.images+json)
```

### 15.2 Artifact Type Conventions

| Artifact Type | Description | Producer |
|---------------|-------------|----------|
| `application/vnd.productmd.compose+json` | Core compose bundle | Core pipeline |
| `application/vnd.productmd.images+json` | Images metadata (core or supplementary) | Any pipeline producing images |
| `application/vnd.productmd.pipeline-status+json` | Pipeline execution status | Each pipeline (multiple revisions) |
| `application/vnd.productmd.pipeline-manifest+json` | Expected pipelines declaration (optional) | Orchestrator or setup |

### 15.3 Attachment Schema

Supplementary metadata files use the **same schema as core metadata files**.

**Example: cloud-images.json**
```json
{
  "header": {
    "version": "2.0",
    "type": "productmd.images"
  },
  "payload": {
    "compose": {
      "id": "Fedora-39-20231201.0",
      "type": "production",
      "date": "20231201",
      "respin": 0
    },
    "images": {
      "Server": {
        "x86_64": [
          {
            "location": {
              "url": "oci://quay.io/fedora/cloud:server-39-x86_64@sha256:...",
              "size": 536870912,
              "checksum": "sha256:...",
              "local_path": "Server/x86_64/images/Fedora-Server-39-x86_64.qcow2"
            },
            "type": "qcow2",
            "format": "qcow2",
            "arch": "x86_64",
            "subvariant": "Server"
          }
        ]
      }
    }
  }
}
```

### 15.4 Publishing Workflow

**Core pipeline:**
```bash
# Build core artifacts and metadata
productmd-upgrade --input /compose --output /tmp/v2 --compute-checksums

# Push to registry as OCI artifact
oras push quay.io/fedora/compose:39-20231201.0 \
  --artifact-type application/vnd.productmd.compose+json \
  composeinfo.json \
  rpms.json \
  images.json \
  extra_files.json
```

**Supplementary pipeline:**
```bash
# Get core manifest digest
CORE_DIGEST=$(oras manifest fetch quay.io/fedora/compose:39-20231201.0 | \
              jq -r '.config.digest')

# Attach supplementary metadata
oras attach quay.io/fedora/compose@${CORE_DIGEST} \
  --artifact-type application/vnd.productmd.images+json \
  cloud-images.json
```

---

## 16. Pipeline Status Tracking

### 16.1 Purpose

Each pipeline publishes status updates to communicate:
- When it started
- Whether it's in progress, complete, or failed
- Maximum expected duration (for timeout detection)
- Logs and debugging information

This enables clients to:
- Detect when all expected pipelines have finished
- Distinguish "still running" from "failed"
- Handle catastrophic failures (where pipeline can't update status)

### 16.2 Status Schema

**Required fields:**
```json
{
  "pipeline_id": "string (unique identifier for this pipeline instance)",
  "status": "in_progress | complete | failed",
  "revision": 1,
  "started_at": "ISO 8601 timestamp",
  "max_duration_hours": 4,
  "compose_id": "Fedora-39-20231201.0"
}
```

**Optional/recommended fields:**
```json
{
  "pipeline_name": "cloud-images (human-readable name)",
  "completed_at": "ISO 8601 timestamp (for complete/failed)",
  "failed_at": "ISO 8601 timestamp (for failed)",
  "error": "Error message (for failed)",
  "logs_url": "https://ci.example.com/job/12345",
  "builder_version": "2.3.1"
}
```

Pipelines may add any additional fields useful for debugging or monitoring.

### 16.3 Status Lifecycle

**1. Pipeline starts:**
```bash
# Attach initial status
cat > status-v1.json <<EOF
{
  "pipeline_id": "cloud-images-20231201-001",
  "pipeline_name": "cloud-images",
  "status": "in_progress",
  "revision": 1,
  "started_at": "2023-12-01T10:00:00Z",
  "max_duration_hours": 4,
  "compose_id": "Fedora-39-20231201.0"
}
EOF

oras attach quay.io/fedora/compose@${CORE_DIGEST} \
  --artifact-type application/vnd.productmd.pipeline-status+json \
  status-v1.json
```

**2. Pipeline completes successfully:**
```bash
cat > status-v2.json <<EOF
{
  "pipeline_id": "cloud-images-20231201-001",
  "pipeline_name": "cloud-images",
  "status": "complete",
  "revision": 2,
  "started_at": "2023-12-01T10:00:00Z",
  "completed_at": "2023-12-01T12:30:00Z",
  "compose_id": "Fedora-39-20231201.0",
  "logs_url": "https://ci.example.com/job/12345"
}
EOF

oras attach quay.io/fedora/compose@${CORE_DIGEST} \
  --artifact-type application/vnd.productmd.pipeline-status+json \
  status-v2.json
```

**3. Pipeline fails:**
```bash
cat > status-v2.json <<EOF
{
  "pipeline_id": "cloud-images-20231201-001",
  "pipeline_name": "cloud-images",
  "status": "failed",
  "revision": 2,
  "started_at": "2023-12-01T10:00:00Z",
  "failed_at": "2023-12-01T11:15:00Z",
  "compose_id": "Fedora-39-20231201.0",
  "error": "Image build failed: insufficient disk space on build worker",
  "logs_url": "https://ci.example.com/job/12345"
}
EOF

oras attach quay.io/fedora/compose@${CORE_DIGEST} \
  --artifact-type application/vnd.productmd.pipeline-status+json \
  status-v2.json
```

**4. Catastrophic failure (pipeline crashes):**
```
Pipeline started at 10:00, max_duration_hours = 4
Current time: 15:00 (5 hours later)

Client logic:
  if started_at + max_duration_hours < now():
      status = "timeout_failure"
```

### 16.4 Pipeline ID Coordination

Pipeline IDs must be unique within a compose. Coordination strategies:

- **Convention-based**: `"cloud-images"`, `"container-images"` (teams coordinate)
- **UUID**: `"550e8400-e29b-41d4-a716-446655440000"` (guaranteed unique)
- **Composite**: `"cloud-images-20231201-001"` (name + date + sequence)

Choice is left to the implementation team.

---

## 17. Pipeline Manifest (Optional)

### 17.1 Purpose

An optional manifest declares which supplementary pipelines are expected for a
compose. This enables:

- Clients to know when to stop waiting for more attachments
- Clear completion criteria (all expected pipelines finished)
- Progress tracking during compose creation

**Note:** If an artifact is truly required for a valid compose, it belongs in
the core pipeline. Supplementary pipelines by definition are things that can
fail without invalidating the core compose.

### 17.2 Schema

```json
{
  "compose_id": "Fedora-39-20231201.0",
  "expected_pipelines": [
    "cloud-images",
    "container-images",
    "vagrant-images"
  ],
  "created_at": "2023-12-01T09:55:00Z"
}
```

### 17.3 Who Publishes the Manifest?

The manifest is **optional** and can be published by:

- **CI/CD orchestrator** (knows what pipelines it will trigger)
- **Setup/planning phase** (before core pipeline runs)
- **Core pipeline** (if it knows about supplementary pipelines)
- **Nobody** (composes work without a manifest using best-effort mode)

### 17.4 Publishing the Manifest

```bash
oras attach quay.io/fedora/compose@${CORE_DIGEST} \
  --artifact-type application/vnd.productmd.pipeline-manifest+json \
  pipeline-manifest.json
```

---

## 18. Client Behavior with Attachments

### 18.1 Unified Abstraction

The ProductMD library presents a **unified view** of core + all attachments.
Consumers don't need to know about the attachment mechanism.

**API (unchanged from Phase 1):**
```python
# Works with both filesystem and OCI references
compose = productmd.Compose("oci://quay.io/fedora/compose:39-20231201.0")

# Returns ALL images: core + cloud + container + any other attachments
# Library internally discovers and merges everything
all_images = compose.images
```

### 18.2 Localization with Attachments

The `productmd-localize` tool treats core + attachments as a unified dataset:

```bash
productmd-localize \
  --input oci://quay.io/fedora/compose:39-20231201.0 \
  --output /mnt/local-compose \
  --skip-type iso  # Optional filtering by image type
```

**Process:**
1. Load core metadata from OCI
2. Discover and merge all attachments
3. Download all artifacts from unified view
4. Write v1.2 local compose

**Result:** Local compose contains everything from core and attachments,
indistinguishable in the filesystem layout.

---

## 19. Validation Requirements

### 19.1 Attachment Validation

When merging attachments with core metadata, the library performs **strict validation**:

**Required checks (raises exception on failure):**

1. Compose ID match
2. Metadata version compatibility
3. Variant existence
4. Architecture compatibility

### 19.2 Existing Validation

After merging, the library applies all existing ProductMD validation rules:
- All images have sufficient metadata for unique identification
- Schema validation
- Checksum format validation
- Location URL validation

---

## Appendix C: Glossary

**Attachment**: An OCI artifact referenced via the referrers API that extends
core compose metadata without modifying it (Phase 2).

**Compose**: A complete snapshot of a Linux distribution ready for release,
including metadata, RPMs, images, and repositories.

**Core pipeline**: The primary build pipeline that creates essential artifacts
and publishes the immutable core metadata (Phase 2).

**Location**: An object representing the location and integrity information for
a single artifact (file or repository).

**Localization**: The process of downloading remote artifacts to local storage
and recreating the v1.2 filesystem layout.

**local_path**: A relative path that specifies where an artifact should be
placed in the v1.2 filesystem layout.

**OCI**: Open Container Initiative - a standard for container images and
registries.

**Pipeline manifest**: Optional metadata declaring expected supplementary
pipelines for completion tracking (Phase 2).

**Pipeline status**: Metadata attached by each pipeline to track execution
state, start time, and completion (Phase 2).

**Repomd.xml**: The primary metadata file for a YUM/DNF repository, containing
checksums of all other repository metadata.

**Supplementary pipeline**: An independent build pipeline that attaches
additional metadata (e.g., cloud images) after core completion (Phase 2).

**TreeInfo**: An INI-format metadata file (.treeinfo) used by installers and
boot loaders, typically found on installation media.

**Variant**: A subset of a compose representing a different product offering
(e.g., Server, Workstation).
