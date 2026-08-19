#!/usr/bin/env bash
set -euo pipefail

NODES=("10.2.106.5" "10.2.106.124" "10.2.106.182")
API_PORT=${AEGIS_API_PORT:-18082}
for node in "${NODES[@]}"; do
  echo "== $node =="
  curl --fail --silent "http://$node:$API_PORT/health"
  echo
  curl --fail --silent "http://$node:$API_PORT/api/v1/deployment/status"
  echo
done
