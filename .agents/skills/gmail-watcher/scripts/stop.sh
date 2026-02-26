#!/usr/bin/env bash
set -euo pipefail

PID_FILE="/tmp/gmail-watcher.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "gmail-watcher not running"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
fi
rm -f "$PID_FILE"
echo "gmail-watcher stopped"
