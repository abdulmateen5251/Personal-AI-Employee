#!/usr/bin/env bash
set -euo pipefail

for service in watchdog orchestrator filesystem-watcher finance-watcher gmail-watcher calendar-watcher; do
  pid_file="/tmp/${service}.pid"
  if [[ -f "$pid_file" ]]; then
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid"
    fi
    rm -f "$pid_file"
  fi
done

echo "all known services stopped"
