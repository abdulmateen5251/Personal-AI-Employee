# Personal AI Employee

Bronze-tier foundation with agent-skill based watchers, orchestrator, HITL workflow, and extended integrations (Calendar + Odoo skeleton).

## Architecture

- **Perception:** Gmail, File System, Finance CSV, and Calendar watchers
- **Reasoning:** Orchestrator creates plans and approval files
- **Action:** Human-in-the-loop via `Pending_Approval` → `Approved`/`Rejected`
- **Resilience:** Watchdog monitors and restarts key services

## Prerequisites

- Linux/macOS shell
- Python 3.11+
- Optional: Gmail/Calendar OAuth credentials
- Optional: Local Odoo 19 instance

## Setup

1. Create and activate Python environment.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure `.env` values (vault path, API tokens, Odoo/Google settings).

## Quick Start (MVP)

Start only the minimum required stack:

1. Start filesystem watcher:
   ```bash
   bash .agents/skills/filesystem-watcher/scripts/start.sh
   ```
2. Start orchestrator:
   ```bash
   bash .agents/skills/orchestrator/scripts/start.sh
   ```
3. Drop any file into `Vault/Inbox`.
4. Check outputs in `Vault/Needs_Action`, `Vault/Plans`, and `Vault/Done`.

## Run Full Stack

Use watchdog to manage all core services:

```bash
bash .agents/skills/watchdog/scripts/start.sh
bash .agents/skills/watchdog/scripts/status.sh
```

Stop all known services:

```bash
bash .agents/skills/watchdog/scripts/stop-all.sh
```

## Run Individual Services

```bash
bash .agents/skills/gmail-watcher/scripts/start.sh
bash .agents/skills/filesystem-watcher/scripts/start.sh
bash .agents/skills/finance-watcher/scripts/start.sh
bash .agents/skills/calendar-watcher/scripts/start.sh
bash .agents/skills/orchestrator/scripts/start.sh
```

## OAuth Setup (One-Time)

For Gmail:

```bash
.venv/bin/python .agents/skills/gmail-watcher/scripts/gmail_oauth_setup.py
```

For Google Calendar:

```bash
.venv/bin/python .agents/skills/calendar-watcher/scripts/calendar_oauth_setup.py
```

## Odoo Integration (Skeleton)

Start Odoo MCP-style server:

```bash
bash .agents/skills/odoo-integration/scripts/start-server.sh
```

Verify Odoo connection:

```bash
.venv/bin/python .agents/skills/odoo-integration/scripts/verify.py
```

## Folder Flow

- `Vault/Inbox` → file drops
- `Vault/Needs_Action` → incoming tasks
- `Vault/Plans` → generated plans
- `Vault/Pending_Approval` → requires human action
- `Vault/Approved` / `Vault/Rejected` → human decisions
- `Vault/Done` → archived processed files
- `Vault/Logs` → JSON audit logs

## Troubleshooting

- Check logs:
  - `/tmp/filesystem-watcher.log`
  - `/tmp/orchestrator.log`
  - `/tmp/watchdog.log`
- If service stuck, stop and restart:
  ```bash
  bash .agents/skills/watchdog/scripts/stop-all.sh
  bash .agents/skills/watchdog/scripts/start.sh
  ```

## Vault Path

`/home/abdul-matten/Desktop/Personal-AI-Employee /Vault`
