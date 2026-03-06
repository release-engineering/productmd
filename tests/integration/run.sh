#!/bin/bash
# Run productmd integration tests using container compose.
#
# Supports podman-compose, podman compose, docker compose, and docker-compose.
# Starts an HTTP server, TLS-enabled OCI registry, seeds the registry with
# test artifacts, and runs the integration test suite.
#
# Usage:
#   ./tests/integration/run.sh
#
# The script will:
#   1. Detect the available compose tool (podman or docker)
#   2. Build registry image first (generates TLS certs at build time)
#   3. Build remaining images (they COPY the CA cert from the registry image)
#   4. Start infrastructure services (registry, httpserver, registry-seed)
#   5. Wait for registry to be seeded
#   6. Wait for generated OCI metadata to be served via HTTP
#   7. Run test-runner container
#   8. Tear down all services
#   9. Exit with the test runner's exit code
set -e

cd "$(dirname "$0")"

# Detect compose tool
if command -v podman-compose &> /dev/null; then
    COMPOSE="podman-compose"
elif command -v podman &> /dev/null && podman compose version &> /dev/null 2>&1; then
    COMPOSE="podman compose"
elif command -v docker &> /dev/null && docker compose version &> /dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE="docker-compose"
else
    echo "Error: No container compose tool found."
    echo "Install one of: podman-compose, podman compose, docker compose, docker-compose"
    exit 1
fi

echo "Using compose tool: ${COMPOSE}"
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up..."
    $COMPOSE down -v 2>/dev/null || true
}
trap cleanup EXIT

# Build registry image first — it generates TLS certificates at build
# time. The other images use COPY --from=integration_registry to get
# the CA cert, so the registry image must exist before they build.
echo "Building registry image (generates TLS certs)..."
$COMPOSE build registry

echo "Building remaining images..."
$COMPOSE build registry-seed test-runner

# Start infrastructure services
echo "Starting infrastructure services..."
$COMPOSE up -d registry httpserver registry-seed

# Wait for registry seed to complete by checking the catalog.
# Uses -k (insecure) for the host-side check since the self-signed CA
# is only trusted inside the containers.
echo "Waiting for registry to be seeded..."
for i in $(seq 1 60); do
    COUNT=$(curl -sk https://localhost:5000/v2/_catalog 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data.get('repositories', [])))
except:
    print(0)
" 2>/dev/null || echo 0)
    if [ "$COUNT" -ge 3 ]; then
        echo "Registry seeded with ${COUNT} repositories."
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo "Error: Timed out waiting for registry to be seeded."
        echo "Registry-seed logs:"
        $COMPOSE logs registry-seed
        exit 1
    fi
    sleep 1
done

# Wait for generated OCI metadata to be available via HTTP
echo "Waiting for generated OCI metadata..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8080/oci-metadata/images-oci.json > /dev/null 2>&1; then
        echo "OCI metadata available."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "Error: Timed out waiting for OCI metadata."
        exit 1
    fi
    sleep 1
done

# Run the test-runner container
echo ""
echo "Running integration tests..."
echo ""
$COMPOSE run --rm test-runner
EXIT_CODE=$?

echo ""
echo "Integration tests finished with exit code: ${EXIT_CODE}"
exit $EXIT_CODE
