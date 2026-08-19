#!/usr/bin/env bash
set -euo pipefail

# Deploys the current checkout to three already-provisioned Linux nodes.
# Authentication is intentionally delegated to the operator's SSH agent/key.

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
NODES=("10.2.106.5" "10.2.106.124" "10.2.106.182")
CONTROL_NODE="10.2.106.5"
REMOTE_ROOT="/opt/aegis-ai"
VERSION=${AEGIS_DEPLOYMENT_VERSION:-three-node-demo-$(date +%Y%m%d%H%M%S)}

# The control node serves the compiled Vite bundle; build it locally so Node.js
# is not required on the CentOS application hosts.
if [[ ! -f "$ROOT_DIR/apps/web/dist/index.html" ]]; then
  command -v npm >/dev/null 2>&1 || { echo "npm is required to build apps/web/dist" >&2; exit 1; }
  (cd "$ROOT_DIR/apps/web" && VITE_ENV="${VITE_ENV:-development}" VITE_API_BASE_URL="http://$CONTROL_NODE:18082/api/v1" npm run build)
fi

for node in "${NODES[@]}"; do
  role=worker-ops
  [[ "$node" == "$CONTROL_NODE" ]] && role=control
  [[ "$node" == "10.2.106.124" ]] && role=worker-ai
  echo "[deploy] preparing $node ($role)"
  ssh "root@$node" "install -d -m 0750 $REMOTE_ROOT /etc/aegis-ai /var/log/aegis-ai; id aegis >/dev/null 2>&1 || useradd --system --home-dir $REMOTE_ROOT --shell /sbin/nologin aegis"
  tar \
    --exclude=.git \
    --exclude=apps/web/node_modules \
    --exclude=backend/.venv \
    -czf - -C "$ROOT_DIR" backend deploy apps/web/dist scripts/migrate_platform_tidb.py scripts/tidb-production-setup.sql scripts/verify-tidb-platform.py | ssh "root@$node" "tar -xzf - -C $REMOTE_ROOT"
  ssh "root@$node" "install -d -m 0750 $REMOTE_ROOT/data/datasets $REMOTE_ROOT/web $REMOTE_ROOT/scripts; cp -a $REMOTE_ROOT/apps/web/dist/. $REMOTE_ROOT/web/; chown -R aegis:aegis $REMOTE_ROOT /var/log/aegis-ai; sed -e 's/^AEGIS_NODE_ROLE=.*/AEGIS_NODE_ROLE=$role/' -e 's/^AEGIS_DEPLOYMENT_VERSION=.*/AEGIS_DEPLOYMENT_VERSION=$VERSION/' -e 's/^AEGIS_WEB_PORT=.*/AEGIS_WEB_PORT=18081/' $REMOTE_ROOT/deploy/three-node.env.example > /etc/aegis-ai/aegis.env; cp $REMOTE_ROOT/deploy/systemd/aegis-api.service /etc/systemd/system/aegis-api.service; cp $REMOTE_ROOT/deploy/systemd/aegis-web.service /etc/systemd/system/aegis-web.service; python3.9 -m venv $REMOTE_ROOT/venv; $REMOTE_ROOT/venv/bin/python -m pip install --disable-pip-version-check -q --upgrade 'pip>=24,<25' 'setuptools>=70,<81' 'wheel>=0.43,<1'; $REMOTE_ROOT/venv/bin/python -m pip install --disable-pip-version-check -q -r $REMOTE_ROOT/backend/requirements.txt; chown -R aegis:aegis $REMOTE_ROOT /etc/aegis-ai; systemctl daemon-reload; systemctl enable aegis-api.service; systemctl restart aegis-api.service"
  if [[ "$node" == "$CONTROL_NODE" ]]; then
    ssh "root@$node" "systemctl enable aegis-web.service; systemctl restart aegis-web.service"
  fi
done

echo "[deploy] completed version=$VERSION"
echo "[deploy] web: http://$CONTROL_NODE:18081"
echo "[deploy] api: http://$CONTROL_NODE:18082/docs"
