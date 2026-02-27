#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"

bash "$ROOT_DIR/.agents/skills/filesystem-watcher/scripts/start.sh"
bash "$ROOT_DIR/.agents/skills/gmail-watcher/scripts/start.sh"
bash "$ROOT_DIR/.agents/skills/finance-watcher/scripts/start.sh"
bash "$ROOT_DIR/.agents/skills/gmail-send-mcp/scripts/start.sh"
bash "$ROOT_DIR/.agents/skills/linkedin-poster/scripts/start.sh"
bash "$ROOT_DIR/.agents/skills/social-poster/scripts/start.sh"
bash "$ROOT_DIR/.agents/skills/ceo-briefing/scripts/start.sh"
bash "$ROOT_DIR/.agents/skills/odoo-integration/scripts/start-server.sh"
bash "$ROOT_DIR/.agents/skills/orchestrator/scripts/start.sh"
bash "$ROOT_DIR/.agents/skills/watchdog/scripts/start.sh"

echo "All services started."