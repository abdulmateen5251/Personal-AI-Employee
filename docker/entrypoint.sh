#!/usr/bin/env bash
set -euo pipefail

cd /app

export VAULT_PATH="${VAULT_PATH:-/app/Vault}"
export AGENT_ZONE="${AGENT_ZONE:-local}"
export DRY_RUN="${DRY_RUN:-true}"

# Ensure required Vault directories exist
mkdir -p "$VAULT_PATH/Inbox" \
         "$VAULT_PATH/Needs_Action" \
         "$VAULT_PATH/Pending_Approval" \
         "$VAULT_PATH/Approved" \
         "$VAULT_PATH/Rejected" \
         "$VAULT_PATH/Done" \
         "$VAULT_PATH/Plans" \
         "$VAULT_PATH/Logs" \
         "$VAULT_PATH/Schedules"

echo "[entrypoint] Starting AI Employee services..."

python3 .agents/skills/filesystem-watcher/scripts/filesystem_watcher.py \
  >/tmp/filesystem-watcher.log 2>&1 &
FS_PID=$!
echo "[entrypoint] filesystem-watcher PID=$FS_PID"

python3 .agents/skills/gmail-watcher/scripts/gmail_watcher.py \
  >/tmp/gmail-watcher.log 2>&1 &
GMAIL_PID=$!
echo "[entrypoint] gmail-watcher PID=$GMAIL_PID"

python3 .agents/skills/orchestrator/scripts/orchestrator.py \
  >/tmp/orchestrator.log 2>&1 &
ORCH_PID=$!
echo "[entrypoint] orchestrator PID=$ORCH_PID"

cleanup() {
  echo "[entrypoint] Shutting down..."
  kill "$FS_PID" "$GMAIL_PID" "$ORCH_PID" 2>/dev/null || true
  wait "$FS_PID" "$GMAIL_PID" "$ORCH_PID" 2>/dev/null || true
}

trap cleanup SIGINT SIGTERM

# Stream orchestrator log to stdout so docker logs works
tail -f /tmp/orchestrator.log &
TAIL_PID=$!

wait -n "$FS_PID" "$GMAIL_PID" "$ORCH_PID"
EXIT_CODE=$?
kill "$TAIL_PID" 2>/dev/null || true
cleanup
exit "$EXIT_CODE"
