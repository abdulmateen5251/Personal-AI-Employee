#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
PID_FILE="/tmp/finance-watcher.pid"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "finance-watcher already running"
  exit 0
fi

cd "$ROOT_DIR"
nohup "$PYTHON_BIN" .agents/skills/finance-watcher/scripts/finance_watcher.py >/tmp/finance-watcher.log 2>&1 &
echo $! > "$PID_FILE"
echo "finance-watcher started (pid $(cat "$PID_FILE"))"
