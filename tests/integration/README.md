# Integration Tests

End-to-end tests for the `productmd` CLI tools using containerized services.

## Prerequisites

- `podman` with `podman-compose` or `podman compose`, **or** `docker` with `docker compose`
- Network access to pull container images (`nginx:alpine`, `python:3.11-slim`,
  `ghcr.io/oras-project/oras:v1.2.0`, `fedora:43`, `registry:2`)

## Services

| Service | Image | Purpose |
|---------|-------|---------|
| **httpserver** | `nginx:alpine` | Serves v1.2 compose fixtures and generated v2.0 OCI metadata via HTTP |
| **registry** | Custom (`Containerfile.registry`) | TLS-enabled OCI registry with self-signed certs generated at build time |
| **registry-seed** | Custom (`Containerfile.registry-seed`) | Pushes 6 artifacts to the registry and generates v2.0 metadata with real OCI digests |
| **test-runner** | Custom (`Containerfile.test-runner`) | Waits for all services, then runs pytest |

The registry generates TLS certificates in a multi-stage build. Other
containers get the CA cert via a configurable `REGISTRY_IMAGE` build arg
(defaults to `localhost/integration_registry` for podman, automatically
set to `integration_registry` for docker). The `run.sh` script builds
the registry image first.

## Running

### Automated (recommended)

```bash
./tests/integration/run.sh
```

### Manual (podman)

```bash
cd tests/integration
podman-compose build registry
podman-compose build registry-seed test-runner
podman-compose up -d registry httpserver registry-seed
podman-compose logs -f registry-seed   # wait for seed
podman-compose run --rm test-runner
podman-compose down -v
```

### Manual (docker)

```bash
cd tests/integration
export REGISTRY_IMAGE=integration_registry
docker compose build registry
docker compose build registry-seed test-runner
docker compose up -d registry httpserver registry-seed
docker compose logs -f registry-seed   # wait for seed
docker compose run --rm test-runner
docker compose down -v
```

## Test Fixtures

`fixtures/compose/` contains a minimal v1.2 compose with fake artifacts
for x86_64 and aarch64 (ISOs, RPMs, GPL files). Metadata files contain
real SHA-256 checksums.

The registry-seed generates v2.0 OCI metadata at runtime with real digests,
served at `/oci-metadata/` by the httpserver.

## Isolation

Integration tests are excluded from unit test runs:

```toml
# pyproject.toml
[tool.pytest.ini_options]
addopts = "--ignore=tests/integration"
```

## Debugging

```bash
curl http://localhost:8080/metadata/images.json | python3 -m json.tool
curl -sk https://localhost:5000/v2/_catalog
curl http://localhost:8080/oci-metadata/images-oci.json | python3 -m json.tool
podman-compose logs registry-seed  # or: docker compose logs registry-seed
```
