#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
PID_FILE="/tmp/odoo-mcp.pid"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "odoo-mcp already running"
  exit 0
fi

cd "$ROOT_DIR/.agents/skills/odoo-integration/scripts"
nohup "$PYTHON_BIN" odoo_mcp_server.py >/tmp/odoo-mcp.log 2>&1 &
echo $! > "$PID_FILE"
echo "odoo-mcp started (pid $(cat "$PID_FILE"))"
