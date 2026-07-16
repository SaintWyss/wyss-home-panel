#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$project_dir"

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e 'bridge[dev]'

mkdir -p bridge/data
mkdir -p "$HOME/.config/systemd/user"
sed "s|@PROJECT_DIR@|$project_dir|g" scripts/wyss-panel-bridge.service.in \
  > "$HOME/.config/systemd/user/wyss-panel-bridge.service"
systemctl --user daemon-reload
systemctl --user enable --now wyss-panel-bridge.service
echo "Yo instalé el puente como servicio del usuario."
