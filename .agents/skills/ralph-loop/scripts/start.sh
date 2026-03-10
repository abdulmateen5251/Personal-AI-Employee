#!/usr/bin/env bash
# Start the Ralph persistence loop wrapping Qwen Code agent.
# Usage: bash start.sh [--command "..."] [--done-file "..."] [--max-iterations N]
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
PID_FILE="/tmp/ralph-loop.pid"
LOG_FILE="/tmp/ralph-loop.log"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "ralph-loop already running (pid $(cat "$PID_FILE"))"
  exit 0
fi

# Default: run qwen_agent.py --once as the command (so ralph re-runs it)
COMMAND="${RALPH_COMMAND:-$PYTHON_BIN .agents/skills/qwen-agent/scripts/qwen_agent.py --once}"
DONE_FILE="${RALPH_DONE_FILE:-}"
MAX_ITER="${RALPH_MAX_ITER:-20}"
SLEEP_SEC="${RALPH_SLEEP_SEC:-15}"

cd "$ROOT_DIR"

RALPH_ARGS=(
  --command "$COMMAND"
  --max-iterations "$MAX_ITER"
  --sleep-seconds "$SLEEP_SEC"
)
if [[ -n "$DONE_FILE" ]]; then
  RALPH_ARGS+=(--done-file "$DONE_FILE")
fi

nohup "$PYTHON_BIN" .agents/skills/ralph-loop/scripts/ralph_loop.py \
  "${RALPH_ARGS[@]}" \
  >"$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "ralph-loop started (pid $(cat "$PID_FILE"))"
echo "Command: $COMMAND"
echo "Logs: $LOG_FILE"
