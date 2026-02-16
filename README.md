# ProductMD

[![CI](https://github.com/release-engineering/productmd/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/release-engineering/productmd/actions/workflows/ci.yml)
[![PyPI - Version](https://img.shields.io/pypi/v/productmd)](https://pypi.org/project/productmd)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/productmd)](https://pypi.org/project/productmd)
[![License: LGPL v2.1](https://img.shields.io/badge/License-LGPL_v2.1-blue.svg)](https://www.gnu.org/licenses/lgpl-2.1)

**ProductMD** is a Python library for parsing and creating metadata files for OS installation media and compose outputs. It provides structured access to `.treeinfo`, `.discinfo`, and compose metadata files used in Fedora, RHEL, and other RPM-based Linux distributions.

## Features

- **Compose Metadata** - Parse and manipulate compose information, RPM manifests, module metadata, and image manifests
- **TreeInfo** - Read and write `.treeinfo` files describing installable trees
- **DiscInfo** - Handle `.discinfo` files for installation media identification
- **HTTP Support** - Load metadata directly from remote URLs
- **Validation** - Built-in schema validation for metadata integrity

## v2.0 Roadmap — Distributed Compose Metadata

ProductMD 2.0 introduces support for **distributed composes** where artifacts
(RPMs, images, repositories) can be stored in different locations and referenced
via HTTPS URLs or OCI registry references. The metadata includes checksums for
data integrity verification and supports bidirectional conversion between v2.0
(distributed) and v1.2 (local) formats.

> See [PRODUCTMD-2.0-PLAN.md](PRODUCTMD-2.0-PLAN.md) for the full specification.

### Phase 1: Core Infrastructure

- [x] Implement `version.py` — version constants, `VersionedMetadataMixin`, detection utilities
- [x] Add version conversion functions (`version_to_string`, `string_to_version`, `get_version_tuple`)
- [x] Add version detection (`detect_version_from_data`, `is_v1`, `is_v2`)
- [x] Export version API from `productmd/__init__.py`
- [x] Write unit tests for version module
- [ ] Implement `Location` class with full validation
- [ ] Implement `FileEntry` class for OCI image contents
- [ ] Add checksum computation utilities (`compute_checksum`)
- [ ] Add URL scheme detection (`is_remote`, `is_oci`)
- [ ] Add OCI image layer extraction utilities

### Phase 2: Metadata Classes

- [ ] Update `VERSION` to `(2, 0)` in `productmd/common.py`
- [ ] Update `VariantPaths` to use Location objects
- [ ] Update `Rpms.add()` to accept Location objects
- [ ] Update `Image` class to use `location` attribute
- [ ] Implement `ExtraFiles` class with `add()` method
- [ ] Implement v2.0 serialization for all metadata classes
- [ ] Implement v2.0 deserialization for all metadata classes
- [ ] Support v1.2 serialization/deserialization (backward compat)
- [ ] Write unit tests for each metadata class

### Phase 3: Conversion Utilities

- [ ] Implement `upgrade_to_v2()` function
- [ ] Implement `downgrade_to_v1()` function
- [ ] Implement `iter_all_locations()` generator
- [ ] Write conversion tests (round-trip validation)

### Phase 4: Localization Tool

- [ ] Implement `localize_compose()` function
- [ ] Implement parallel download with progress tracking
- [ ] Implement OCI registry download support (using skopeo/oras)
- [ ] Implement OCI image layer extraction for `contents` field
- [ ] Implement HTTPS download with retry logic
- [ ] Implement checksum verification
- [ ] Write integration tests

### Phase 5: CLI Tools

- [ ] Create `productmd-upgrade` command
- [ ] Create `productmd-downgrade` command
- [ ] Create `productmd-localize` command
- [ ] Create `productmd-verify` command
- [ ] Add man pages and help documentation

### Phase 6: Documentation

- [ ] Write `doc/productmd-2.0.rst` — Complete format specification
- [ ] Write `doc/migration-guide.rst` — v1.2 → v2.0 migration
- [ ] Write `doc/distributed-composes.rst` — Use cases and patterns
- [ ] Update existing docs: `doc/composeinfo.rst`, `doc/rpms.rst`, etc.
- [ ] Add code examples and tutorials

### Phase 7: Testing & Validation

- [ ] Write comprehensive test suite (>90% coverage)
- [ ] Test with real Fedora/RHEL composes
- [ ] Performance testing with large composes
- [ ] Integration testing with existing tools
- [ ] Create test fixtures for v2.0 metadata

## Documentation

Full documentation is available at [productmd.readthedocs.io](http://productmd.readthedocs.io/en/latest/).

## Development

### Prerequisites

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

### Running Tests

```bash
# Run the full test suite
uvx tox

# List available test environments
uvx tox list

# Run a specific environment
uvx tox -e py312
```
> [!IMPORTANT]
> #### Testing with Python 3.6
>
>Python 3.6 is EOL and incompatible with modern tooling. Use the provided container for legacy testing:
>
>```bash
>podman build -f Containerfile.py36 -t productmd-py36-test .
>podman run --rm productmd-py36-test
>```
>
>For an interactive shell: `podman run --rm -it productmd-py36-test /bin/bash`

### Code Quality

```bash
# Run linter
uvx tox -e lint

# Run formatter
uvx tox -e format

# Run security scanner
uvx tox -e bandit
```

### Documentation

```bash
# Build HTML documentation
uvx tox -e docs
```

The generated pages are written to `doc/_build/html/`. Open `doc/_build/html/index.html` in a browser to view them.

### Building

```bash
uv build
```
This will generate the **source** and **wheel** packages under the `dist` directory.

### Releasing

To release a new version and publish to PyPI:

1. **Bump the version** in `pyproject.toml`:

   ```bash
   uv version <new_version>
   ```

   See [uv version docs](https://docs.astral.sh/uv/reference/cli/#uv-version) for other version commands (e.g., `uv version --bump minor`).

2. **Commit and push** the version change:

   ```bash
   git add pyproject.toml uv.lock
   git commit -m "Bump version to <new_version>"
   git push origin master
   ```

3. **Create a GitHub release**:
   - Go to [Releases](../../releases) and click **"Create a new release"**
   - Pin the release to a tag following the format `vX.X` (e.g., `v1.0`, `v2.1`)
   - Fill in the release title and notes
   - Click **"Publish release"**

4. **Automated publishing**:
   - Publishing the release triggers the CI pipeline
   - If CI passes, the CD pipeline automatically builds and publishes the package to PyPI

## License

This project is licensed under the [GNU Lesser General Public License v2.1](LICENSE).
