#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
PID_FILE="/tmp/gmail-send-mcp.pid"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "gmail-send-mcp already running"
  exit 0
fi

cd "$ROOT_DIR"
nohup "$PYTHON_BIN" .agents/skills/gmail-send-mcp/scripts/gmail_send_mcp.py >/tmp/gmail-send-mcp.log 2>&1 &
echo $! > "$PID_FILE"
echo "gmail-send-mcp started (pid $(cat "$PID_FILE"))"
