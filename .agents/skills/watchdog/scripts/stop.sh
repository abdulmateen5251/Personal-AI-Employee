#!/usr/bin/env bash
set -euo pipefail

PID_FILE="/tmp/watchdog.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "watchdog not running"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
fi
rm -f "$PID_FILE"
echo "watchdog stopped"
