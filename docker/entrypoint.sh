#!/usr/bin/env bash
set -euo pipefail

cd /app

export VAULT_PATH="${VAULT_PATH:-/app/Vault}"
export AGENT_ZONE="${AGENT_ZONE:-local}"
export DRY_RUN="${DRY_RUN:-true}"

python3 .agents/skills/filesystem-watcher/scripts/filesystem_watcher.py &
FS_PID=$!

python3 .agents/skills/orchestrator/scripts/orchestrator.py &
ORCH_PID=$!

cleanup() {
  kill "$FS_PID" "$ORCH_PID" 2>/dev/null || true
  wait "$FS_PID" "$ORCH_PID" 2>/dev/null || true
}

trap cleanup SIGINT SIGTERM

wait -n "$FS_PID" "$ORCH_PID"
EXIT_CODE=$?
cleanup
exit "$EXIT_CODE"
