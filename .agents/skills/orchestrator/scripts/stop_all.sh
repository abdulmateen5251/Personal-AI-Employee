#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../../../.." && pwd)"

bash "$ROOT_DIR/.agents/skills/watchdog/scripts/stop.sh" || true
bash "$ROOT_DIR/.agents/skills/orchestrator/scripts/stop.sh" || true
bash "$ROOT_DIR/.agents/skills/odoo-integration/scripts/stop-server.sh" || true
bash "$ROOT_DIR/.agents/skills/ceo-briefing/scripts/stop.sh" || true
bash "$ROOT_DIR/.agents/skills/social-poster/scripts/stop.sh" || true
bash "$ROOT_DIR/.agents/skills/linkedin-poster/scripts/stop.sh" || true
bash "$ROOT_DIR/.agents/skills/gmail-send-mcp/scripts/stop.sh" || true
bash "$ROOT_DIR/.agents/skills/finance-watcher/scripts/stop.sh" || true
bash "$ROOT_DIR/.agents/skills/gmail-watcher/scripts/stop.sh" || true
bash "$ROOT_DIR/.agents/skills/filesystem-watcher/scripts/stop.sh" || true

echo "All services stopped."