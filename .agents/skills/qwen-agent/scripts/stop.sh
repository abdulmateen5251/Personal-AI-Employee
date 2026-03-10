#!/usr/bin/env bash
set -euo pipefail

PID_FILE="/tmp/qwen-agent.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "qwen-agent is not running (no PID file)"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  rm -f "$PID_FILE"
  echo "qwen-agent stopped (pid $PID)"
else
  echo "qwen-agent was not running (stale PID $PID)"
  rm -f "$PID_FILE"
fi
