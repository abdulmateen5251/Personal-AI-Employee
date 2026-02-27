#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"
START_ALL="$ROOT_DIR/.agents/skills/orchestrator/scripts/start_all.sh"
VERIFY_WATCHDOG="$ROOT_DIR/.agents/skills/watchdog/scripts/verify.py"

TMP_CRON="$(mktemp)"
crontab -l 2>/dev/null | grep -v "personal-ai-employee" > "$TMP_CRON" || true

{
  echo "@reboot bash '$START_ALL' # personal-ai-employee"
  echo "*/15 * * * * python3 '$VERIFY_WATCHDOG' >/tmp/personal-ai-employee-health.log 2>&1 # personal-ai-employee"
} >> "$TMP_CRON"

crontab "$TMP_CRON"
rm -f "$TMP_CRON"

echo "Installed cron entries for Personal AI Employee."