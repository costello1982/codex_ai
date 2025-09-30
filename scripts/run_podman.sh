#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME=${IMAGE_NAME:-ipam-app}
CONTAINER_NAME=${CONTAINER_NAME:-ipam-app}
HOST_PORT=${HOST_PORT:-8000}
DB_VOLUME=${DB_VOLUME:-ipam-db}

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)

podman build -t "${IMAGE_NAME}" -f "${PROJECT_ROOT}/Containerfile" "${PROJECT_ROOT}"

if ! podman volume exists "${DB_VOLUME}" >/dev/null 2>&1; then
  podman volume create "${DB_VOLUME}" >/dev/null
fi

if podman ps -a --format '{{.Names}}' | grep -Fxq "${CONTAINER_NAME}"; then
  podman rm -f "${CONTAINER_NAME}" >/dev/null
fi

exec podman run --rm \
  --name "${CONTAINER_NAME}" \
  -p "${HOST_PORT}:8000" \
  -v "${DB_VOLUME}:/app/ipam-data" \
  -e IPAM_DB_PATH=/app/ipam-data/ipam.db \
  "${IMAGE_NAME}"
