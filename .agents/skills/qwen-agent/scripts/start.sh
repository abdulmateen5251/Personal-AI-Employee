#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
PID_FILE="/tmp/qwen-agent.pid"
LOG_FILE="/tmp/qwen-agent.log"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "qwen-agent already running (pid $(cat "$PID_FILE"))"
  exit 0
fi

# Ensure Qwen Code CLI is available
if ! command -v qwen &>/dev/null; then
  echo "ERROR: 'qwen' not found in PATH."
  echo "Install with: npm install -g @qwen-ai/qwen-code"
  exit 1
fi

cd "$ROOT_DIR"
nohup "$PYTHON_BIN" .agents/skills/qwen-agent/scripts/qwen_agent.py \
  --max-items 5 \
  --sleep-seconds 30 \
  >"$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "qwen-agent started (pid $(cat "$PID_FILE"))"
echo "Logs: $LOG_FILE"
