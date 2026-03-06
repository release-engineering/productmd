#!/bin/bash
# Seed the OCI registry with test artifacts for integration testing.
# Waits for the registry to be ready, then pushes fake files via oras.
#
# After pushing, generates v2.0 metadata JSON files with real OCI
# digests into /generated-metadata/ (shared volume with httpserver).
# This is necessary because OCI digests are only known after push.
set -e

REGISTRY="registry:5000"
OUTPUT_DIR="/generated-metadata"

# Wait for registry to be ready (TLS-enabled, CA trusted via SSL_CERT_FILE)
echo "Waiting for registry at ${REGISTRY}..."
until curl -sf --cacert /certs/ca.crt "https://${REGISTRY}/v2/" > /dev/null 2>&1; do
    sleep 1
done
echo "Registry is ready."

cd /fixtures/compose

# ---------------------------------------------------------------------------
# Push artifacts and capture digests
# ---------------------------------------------------------------------------

# x86_64 ISO
ISO_X86_OUTPUT=$(oras push "${REGISTRY}/test/iso:boot-x86_64" \
    Server/x86_64/iso/boot.iso 2>&1)
ISO_X86_DIGEST=$(echo "${ISO_X86_OUTPUT}" | grep -oP 'sha256:[a-f0-9]{64}' | tail -1)
echo "Pushed x86_64 ISO: ${ISO_X86_DIGEST}"

# aarch64 ISO
ISO_AARCH64_OUTPUT=$(oras push "${REGISTRY}/test/iso:boot-aarch64" \
    Server/aarch64/iso/boot.iso 2>&1)
ISO_AARCH64_DIGEST=$(echo "${ISO_AARCH64_OUTPUT}" | grep -oP 'sha256:[a-f0-9]{64}' | tail -1)
echo "Pushed aarch64 ISO: ${ISO_AARCH64_DIGEST}"

# x86_64 RPM
RPM_X86_OUTPUT=$(oras push "${REGISTRY}/test/rpms:bash-x86_64" \
    Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm 2>&1)
RPM_X86_DIGEST=$(echo "${RPM_X86_OUTPUT}" | grep -oP 'sha256:[a-f0-9]{64}' | tail -1)
echo "Pushed x86_64 RPM: ${RPM_X86_DIGEST}"

# aarch64 RPM
RPM_AARCH64_OUTPUT=$(oras push "${REGISTRY}/test/rpms:bash-aarch64" \
    Server/aarch64/os/Packages/b/bash-5.2.26-3.fc41.aarch64.rpm 2>&1)
RPM_AARCH64_DIGEST=$(echo "${RPM_AARCH64_OUTPUT}" | grep -oP 'sha256:[a-f0-9]{64}' | tail -1)
echo "Pushed aarch64 RPM: ${RPM_AARCH64_DIGEST}"

# x86_64 GPL (extra file)
GPL_X86_OUTPUT=$(oras push "${REGISTRY}/test/extra:gpl-x86_64" \
    Server/x86_64/os/GPL 2>&1)
GPL_X86_DIGEST=$(echo "${GPL_X86_OUTPUT}" | grep -oP 'sha256:[a-f0-9]{64}' | tail -1)
echo "Pushed x86_64 GPL: ${GPL_X86_DIGEST}"

# aarch64 GPL (extra file)
GPL_AARCH64_OUTPUT=$(oras push "${REGISTRY}/test/extra:gpl-aarch64" \
    Server/aarch64/os/GPL 2>&1)
GPL_AARCH64_DIGEST=$(echo "${GPL_AARCH64_OUTPUT}" | grep -oP 'sha256:[a-f0-9]{64}' | tail -1)
echo "Pushed aarch64 GPL: ${GPL_AARCH64_DIGEST}"

echo ""
echo "Registry seeded successfully with 6 artifacts."

# ---------------------------------------------------------------------------
# Generate v2.0 metadata JSON with real OCI digests
#
# These files are written to /generated-metadata/ which is a shared
# volume mounted by the httpserver at /usr/share/nginx/html/oci-metadata/
# so tests can fetch them via HTTP.
# ---------------------------------------------------------------------------

echo ""
echo "Generating v2.0 OCI metadata..."

mkdir -p "${OUTPUT_DIR}"

# Compute file checksums (sha256) for the artifacts
ISO_X86_CHECKSUM="sha256:$(sha256sum Server/x86_64/iso/boot.iso | cut -d' ' -f1)"
ISO_AARCH64_CHECKSUM="sha256:$(sha256sum Server/aarch64/iso/boot.iso | cut -d' ' -f1)"
RPM_X86_CHECKSUM="sha256:$(sha256sum Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm | cut -d' ' -f1)"
RPM_AARCH64_CHECKSUM="sha256:$(sha256sum Server/aarch64/os/Packages/b/bash-5.2.26-3.fc41.aarch64.rpm | cut -d' ' -f1)"
GPL_X86_CHECKSUM="sha256:$(sha256sum Server/x86_64/os/GPL | cut -d' ' -f1)"
GPL_AARCH64_CHECKSUM="sha256:$(sha256sum Server/aarch64/os/GPL | cut -d' ' -f1)"

ISO_X86_SIZE=$(stat -c%s Server/x86_64/iso/boot.iso)
ISO_AARCH64_SIZE=$(stat -c%s Server/aarch64/iso/boot.iso)
RPM_X86_SIZE=$(stat -c%s Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm)
RPM_AARCH64_SIZE=$(stat -c%s Server/aarch64/os/Packages/b/bash-5.2.26-3.fc41.aarch64.rpm)
GPL_X86_SIZE=$(stat -c%s Server/x86_64/os/GPL)
GPL_AARCH64_SIZE=$(stat -c%s Server/aarch64/os/GPL)

# --- images-oci.json: all images via OCI ---
cat > "${OUTPUT_DIR}/images-oci.json" <<IMAGES_EOF
{
  "header": {
    "type": "productmd.images",
    "version": "2.0"
  },
  "payload": {
    "compose": {
      "date": "20260204",
      "id": "Test-1.0-20260204.0",
      "respin": 0,
      "type": "production"
    },
    "images": {
      "Server": {
        "x86_64": [
          {
            "arch": "x86_64",
            "bootable": false,
            "disc_count": 1,
            "disc_number": 1,
            "format": "iso",
            "implant_md5": null,
            "mtime": 1738627200,
            "subvariant": "Server",
            "type": "boot",
            "volume_id": "Test-1.0",
            "location": {
              "url": "oci://${REGISTRY}/test/iso:boot-x86_64@${ISO_X86_DIGEST}",
              "size": ${ISO_X86_SIZE},
              "checksum": "${ISO_X86_CHECKSUM}",
              "local_path": "Server/x86_64/iso/boot.iso"
            }
          }
        ],
        "aarch64": [
          {
            "arch": "aarch64",
            "bootable": false,
            "disc_count": 1,
            "disc_number": 1,
            "format": "iso",
            "implant_md5": null,
            "mtime": 1738627200,
            "subvariant": "Server",
            "type": "boot",
            "volume_id": "Test-1.0",
            "location": {
              "url": "oci://${REGISTRY}/test/iso:boot-aarch64@${ISO_AARCH64_DIGEST}",
              "size": ${ISO_AARCH64_SIZE},
              "checksum": "${ISO_AARCH64_CHECKSUM}",
              "local_path": "Server/aarch64/iso/boot.iso"
            }
          }
        ]
      }
    }
  }
}
IMAGES_EOF

# --- images-mixed.json: x86_64 via HTTP, aarch64 via OCI ---
cat > "${OUTPUT_DIR}/images-mixed.json" <<MIXED_EOF
{
  "header": {
    "type": "productmd.images",
    "version": "2.0"
  },
  "payload": {
    "compose": {
      "date": "20260204",
      "id": "Test-1.0-20260204.0",
      "respin": 0,
      "type": "production"
    },
    "images": {
      "Server": {
        "x86_64": [
          {
            "arch": "x86_64",
            "bootable": false,
            "disc_count": 1,
            "disc_number": 1,
            "format": "iso",
            "implant_md5": null,
            "mtime": 1738627200,
            "subvariant": "Server",
            "type": "boot",
            "volume_id": "Test-1.0",
            "location": {
              "url": "http://httpserver:80/Server/x86_64/iso/boot.iso",
              "size": ${ISO_X86_SIZE},
              "checksum": "${ISO_X86_CHECKSUM}",
              "local_path": "Server/x86_64/iso/boot.iso"
            }
          }
        ],
        "aarch64": [
          {
            "arch": "aarch64",
            "bootable": false,
            "disc_count": 1,
            "disc_number": 1,
            "format": "iso",
            "implant_md5": null,
            "mtime": 1738627200,
            "subvariant": "Server",
            "type": "boot",
            "volume_id": "Test-1.0",
            "location": {
              "url": "oci://${REGISTRY}/test/iso:boot-aarch64@${ISO_AARCH64_DIGEST}",
              "size": ${ISO_AARCH64_SIZE},
              "checksum": "${ISO_AARCH64_CHECKSUM}",
              "local_path": "Server/aarch64/iso/boot.iso"
            }
          }
        ]
      }
    }
  }
}
MIXED_EOF

# --- rpms-oci.json: RPMs via OCI ---
cat > "${OUTPUT_DIR}/rpms-oci.json" <<RPMS_EOF
{
  "header": {
    "type": "productmd.rpms",
    "version": "2.0"
  },
  "payload": {
    "compose": {
      "date": "20260204",
      "id": "Test-1.0-20260204.0",
      "respin": 0,
      "type": "production"
    },
    "rpms": {
      "Server": {
        "x86_64": {
          "bash-0:5.2.26-3.fc41.src": {
            "bash-0:5.2.26-3.fc41.x86_64": {
              "path": "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm",
              "sigkey": "a15b79cc",
              "category": "binary",
              "location": {
                "url": "oci://${REGISTRY}/test/rpms:bash-x86_64@${RPM_X86_DIGEST}",
                "size": ${RPM_X86_SIZE},
                "checksum": "${RPM_X86_CHECKSUM}",
                "local_path": "Server/x86_64/os/Packages/b/bash-5.2.26-3.fc41.x86_64.rpm"
              }
            }
          }
        },
        "aarch64": {
          "bash-0:5.2.26-3.fc41.src": {
            "bash-0:5.2.26-3.fc41.aarch64": {
              "path": "Server/aarch64/os/Packages/b/bash-5.2.26-3.fc41.aarch64.rpm",
              "sigkey": "a15b79cc",
              "category": "binary",
              "location": {
                "url": "oci://${REGISTRY}/test/rpms:bash-aarch64@${RPM_AARCH64_DIGEST}",
                "size": ${RPM_AARCH64_SIZE},
                "checksum": "${RPM_AARCH64_CHECKSUM}",
                "local_path": "Server/aarch64/os/Packages/b/bash-5.2.26-3.fc41.aarch64.rpm"
              }
            }
          }
        }
      }
    }
  }
}
RPMS_EOF

# --- extra_files-oci.json: extra files via OCI ---
cat > "${OUTPUT_DIR}/extra_files-oci.json" <<EXTRA_EOF
{
  "header": {
    "type": "productmd.extra_files",
    "version": "2.0"
  },
  "payload": {
    "compose": {
      "date": "20260204",
      "id": "Test-1.0-20260204.0",
      "respin": 0,
      "type": "production"
    },
    "extra_files": {
      "Server": {
        "x86_64": [
          {
            "file": "Server/x86_64/os/GPL",
            "size": ${GPL_X86_SIZE},
            "checksums": {
              "sha256": "$(echo ${GPL_X86_CHECKSUM} | cut -d: -f2)"
            },
            "location": {
              "url": "oci://${REGISTRY}/test/extra:gpl-x86_64@${GPL_X86_DIGEST}",
              "size": ${GPL_X86_SIZE},
              "checksum": "${GPL_X86_CHECKSUM}",
              "local_path": "Server/x86_64/os/GPL"
            }
          }
        ],
        "aarch64": [
          {
            "file": "Server/aarch64/os/GPL",
            "size": ${GPL_AARCH64_SIZE},
            "checksums": {
              "sha256": "$(echo ${GPL_AARCH64_CHECKSUM} | cut -d: -f2)"
            },
            "location": {
              "url": "oci://${REGISTRY}/test/extra:gpl-aarch64@${GPL_AARCH64_DIGEST}",
              "size": ${GPL_AARCH64_SIZE},
              "checksum": "${GPL_AARCH64_CHECKSUM}",
              "local_path": "Server/aarch64/os/GPL"
            }
          }
        ]
      }
    }
  }
}
EXTRA_EOF

echo "Generated v2.0 OCI metadata files:"
ls -la "${OUTPUT_DIR}/"
echo ""
echo "Seed complete."
