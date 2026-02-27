#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
PID_FILE="/tmp/ceo-briefing.pid"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "ceo-briefing already running"
  exit 0
fi

cd "$ROOT_DIR"
nohup "$PYTHON_BIN" .agents/skills/ceo-briefing/scripts/ceo_briefing.py >/tmp/ceo-briefing.log 2>&1 &
echo $! > "$PID_FILE"
echo "ceo-briefing started (pid $(cat "$PID_FILE"))"
