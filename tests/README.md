# Tests

Test suite for the productmd library. Tests are organized into unit tests,
integration tests, and development tools.

## Directory Structure

```
tests/
├── README.md                    # This file
├── mock_cli.py                  # CLI TUI development tool (not a test)
│
├── Unit tests (run via tox)
│   ├── test_common.py           # MetadataBase, Header, Compose classes
│   ├── test_header.py           # Header version handling
│   ├── test_discinfo.py         # DiscInfo metadata
│   ├── test_treeinfo.py         # TreeInfo metadata (.treeinfo files)
│   ├── test_composeinfo.py      # ComposeInfo metadata (legacy unittest)
│   ├── test_composeinfo_v2.py   # ComposeInfo v2.0 Location support
│   ├── test_images.py           # Images metadata (legacy unittest)
│   ├── test_images_v2.py        # Images v2.0 Location support
│   ├── test_rpms.py             # RPMs metadata (legacy unittest)
│   ├── test_rpms_v2.py          # RPMs v2.0 Location support
│   ├── test_extra_files.py      # ExtraFiles metadata (legacy unittest)
│   ├── test_extra_files_v2.py   # ExtraFiles v2.0 Location support
│   ├── test_modules.py          # Modules metadata (legacy unittest)
│   ├── test_modules_v2.py       # Modules v2.0 Location/NSVCA support
│   ├── test_compose.py          # Compose class (directory loading)
│   ├── test_compose_v2.py       # v2.0 fixture structural validation
│   ├── test_version.py          # Version constants and utilities
│   ├── test_location.py         # Location, FileEntry, checksum utilities
│   ├── test_convert.py          # Conversion utilities (upgrade/downgrade/iter)
│   ├── test_localize.py         # Localization tool (download, verify, skip)
│   ├── test_oci.py              # OCI download utilities (requires oras-py)
│   └── test_cli.py              # CLI subcommands and progress display
│
├── Fixture data
│   ├── compose/                 # v1.x compose fixture (used by test_compose.py)
│   ├── compose-legacy/          # Legacy compose fixture
│   ├── compose-v2/metadata/     # v2.0 JSON fixtures (reference examples)
│   ├── images/                  # Image test fixtures (fedora-20, src_move, etc.)
│   ├── discinfo/                # DiscInfo test fixtures
│   └── treeinfo/                # TreeInfo test fixtures
│
└── integration/                 # Integration tests (Docker Compose, see below)
    ├── README.md                # Detailed integration test docs
    ├── compose.yml              # Container compose services
    ├── run.sh                   # Automated test runner script
    └── ...
```

## Running Unit Tests

Unit tests are run via tox and do not require any external services:

```bash
# Full test suite
uv run tox -e py313 -- -v

# Single test file
uv run tox -e py313 -- -v tests/test_images.py

# Single test class
uv run tox -e py313 -- -v tests/test_images.py::TestImages

# Single test method
uv run tox -e py313 -- -v tests/test_images.py::TestImages::test_fedora_20

# Python 3.6 compatibility (requires podman/docker)
podman build -f Containerfile.py36 -t productmd-py36 . && podman run --rm productmd-py36
```

Do NOT use `uv run pytest` directly — use `uv run tox` to ensure proper packaging.

### Test categories

**Legacy tests** (`test_composeinfo.py`, `test_images.py`, `test_rpms.py`, etc.)
use `unittest.TestCase` style. When modifying these, stay consistent with that style.

**New v2.0 tests** (`test_*_v2.py`, `test_cli.py`, `test_convert.py`, etc.)
use pytest-native style: plain classes, `assert` statements, `pytest.raises`,
and `@pytest.mark.parametrize`.

**OCI tests** (`test_oci.py`) require `oras-py` and are automatically skipped
when the package is not installed (e.g., on Python 3.6).

## Integration Tests

Integration tests run the CLI tools end-to-end inside containers with real
HTTP and OCI registry services. They are **not** discovered by the unit test
runner — they live in `tests/integration/` and are excluded via:

```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = "--ignore=tests/integration"
```

### Running integration tests

```bash
# Automated (recommended)
./tests/integration/run.sh

# Manual (from host, faster for iterating)
cd tests/integration
podman compose up --build -d registry httpserver registry-seed
export HTTP_BASE_URL=http://localhost:8080
export REGISTRY_URL=localhost:5000
cd ../..
uv run pytest -v tests/integration/test_integration.py
cd tests/integration && podman compose down -v
```

See `tests/integration/README.md` for full details, interactive debugging,
and all available test cases.

## CLI TUI Development Tool

`tests/mock_cli.py` is a standalone script for developing and testing the
CLI output behaviour of all productmd subcommands. It simulates command
output with configurable delays, artifact counts, and parallelism — no
network or container services required.

### Subcommands

```bash
# Simulate localize (download progress bars)
python tests/mock_cli.py localize
python tests/mock_cli.py localize --artifacts 10 --parallel 4
python tests/mock_cli.py localize --skip 2 --fail 1

# Simulate upgrade --compute-checksums (per-artifact checksum log + progress bar)
python tests/mock_cli.py upgrade
python tests/mock_cli.py upgrade --artifacts 50

# Simulate verify (per-artifact OK/FAIL/SKIP log + progress bar)
python tests/mock_cli.py verify
python tests/mock_cli.py verify --artifacts 20 --fail 2

# Simulate downgrade (instant, just a summary message)
python tests/mock_cli.py downgrade
```

### Options

**localize:**

| Flag | Default | Description |
|------|---------|-------------|
| `--artifacts N` | 6 | Number of artifacts to simulate |
| `--min-delay` | 0.5 | Minimum download time per artifact (seconds) |
| `--max-delay` | 1.0 | Maximum download time per artifact (seconds) |
| `--parallel N` | 1 | Parallel downloads (1 = sequential with progress bars) |
| `--skip N` | 0 | Number of artifacts to simulate as skipped |
| `--fail N` | 0 | Number of artifacts to simulate as failed |
| `--updates N` | 20 | Number of progress updates per artifact |

**upgrade / verify:**

| Flag | Default | Description |
|------|---------|-------------|
| `--artifacts N` | 20 | Number of artifacts to simulate |
| `--min-delay` | 1.0 | Minimum total time (seconds) |
| `--max-delay` | 3.0 | Maximum total time (seconds) |
| `--fail N` | 0 | Number of simulated failures (verify only) |

### Display modes

**Localize — sequential** (`--parallel 1`, default): Shows a per-file ASCII
progress bar that updates in place via `\r`:

```
Server/x86_64/iso/boot.iso                         100% [====================] 512MB/512MB [1.4GB/s]
Server/x86_64/os/.../bash-5.2.26-3.fc41.x86_64.rpm 100% [====================] 1.8MB/1.8MB [5.2MB/s]
```

**Localize — parallel** (`--parallel N`): Shows one-line completion messages
(no per-file bars to avoid terminal corruption):

```
  Server/x86_64/os/GPL                               done  18.1kB  33.0kB/s
  Server/x86_64/iso/boot.iso                         done  512MB   1.1GB/s
```

**Upgrade** (`--compute-checksums`): Per-artifact checksum log above a
progress bar:

```
  sha256:a1b2c3d4e5f6...  Server/x86_64/iso/boot.iso
  sha256:7f8e9d0c1b2a...  Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm
Checksumming: 2/20  10% [==                  ]  Server/x86_64/os/Packages/b/bash-...
```

**Verify**: Per-artifact OK/FAIL/SKIP log above a progress bar:

```
  OK     Server/x86_64/iso/boot.iso
  FAIL   Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm: checksum mismatch
  SKIP   Server/x86_64/os/GPL
Verifying: 3/20  15% [===                 ]  Server/x86_64/os/GPL
```

### TTY detection

Progress bars (the `\r`-updating bottom line) are automatically disabled
when output is redirected to a file/pipe or when the `CI` environment
variable is set. Per-artifact log lines are always printed.

```bash
# Interactive terminal: progress bar shown
python tests/mock_cli.py upgrade --artifacts 5

# Redirected: clean output, no ^M characters
python tests/mock_cli.py upgrade --artifacts 5 2>/tmp/log

# CI environment: no progress bar
CI=true python tests/mock_cli.py upgrade --artifacts 5
```
