#!/usr/bin/env bash
set -euo pipefail

for service in watchdog orchestrator filesystem-watcher finance-watcher gmail-watcher calendar-watcher; do
  pid_file="/tmp/${service}.pid"
  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "${service}: running (pid $(cat "$pid_file"))"
  else
    echo "${service}: stopped"
  fi
done
