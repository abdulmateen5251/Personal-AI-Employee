# Personal AI Employee — Hackathon Build Checklist

> **Target:** Build a fully autonomous "Digital FTE" using Qwen Code CLI + Obsidian Vault.
> **Architecture:** Brain (Qwen Code) → Memory/GUI (Obsidian) → Senses (Python Watchers) → Hands (MCP Servers).

---

## PHASE 0 — Prerequisites & Environment

- [ ] **0.1** Install Python 3.11+ and confirm version (`python3 --version`)
- [ ] **0.2** Create and activate virtual environment
  ```bash
  python3 -m venv .venv && source .venv/bin/activate
  ```
- [ ] **0.3** Install all Python dependencies
  ```bash
  pip install -r requirements.txt
  ```
- [ ] **0.4** Install Qwen Code CLI (`npm install -g @qwen-ai/qwen-code` or equivalent)
- [ ] **0.5** Install Obsidian desktop app and open `Vault/` as a vault
- [ ] **0.6** Copy `.env.example` → `.env` and fill in all required variables:
  - `VAULT_PATH`
  - `GMAIL_CREDENTIALS_PATH` / `GMAIL_TOKEN_PATH`
  - `SENDER_EMAIL` / `RECIPIENT_EMAIL`
  - `LINKEDIN_ACCESS_TOKEN`
  - `FACEBOOK_PAGE_ID` / `FACEBOOK_PAGE_TOKEN`
  - `INSTAGRAM_ACCOUNT_ID` / `INSTAGRAM_ACCESS_TOKEN`
  - `TWITTER_API_KEY` / `TWITTER_API_SECRET` / `TWITTER_ACCESS_TOKEN` / `TWITTER_ACCESS_SECRET`
  - `ODOO_URL` / `ODOO_DB` / `ODOO_USER` / `ODOO_PASSWORD`
- [ ] **0.7** Confirm `.gitignore` covers `.env`, `*.token`, `__pycache__`, `.venv`

---

## PHASE 1 — Vault (Obsidian Memory & GUI)

- [ ] **1.1** Verify all Vault folders exist:
  - `Vault/Inbox/`
  - `Vault/Needs_Action/`
  - `Vault/Plans/`
  - `Vault/Pending_Approval/`
  - `Vault/Approved/`
  - `Vault/Rejected/`
  - `Vault/Done/`
  - `Vault/Logs/`
  - `Vault/Briefings/`
  - `Vault/Invoices/`
  - `Vault/Active_Project/`
  - `Vault/Accounting/Drops/`
  - `Vault/Schedules/`
  - `Vault/Updates/`
- [ ] **1.2** Verify base documents exist and are readable:
  - `Vault/Dashboard.md`
  - `Vault/Company_Handbook.md`
  - `Vault/Business_Goals.md`
- [ ] **1.3** Open Vault in Obsidian — confirm all folders and markdown files render correctly
- [ ] **1.4** **Qwen Code read test** — Run Qwen Code and ask it to read `Vault/Dashboard.md` and print a summary
- [ ] **1.5** **Qwen Code write test** — Ask Qwen Code to append a timestamped test entry to `Vault/Dashboard.md`
- [ ] **1.6** Confirm the written entry appears in Obsidian (live reload)

---

## PHASE 2 — The Brain (Qwen Code CLI + Ralph Loop)

- [ ] **2.1** Confirm Qwen Code CLI launches from project root
  ```bash
  qwen  # or: npx qwen-code
  ```
- [ ] **2.2** Run the Ralph Wiggum Stop hook skill:
  ```bash
  bash .agents/skills/ralph-loop/scripts/start.sh
  ```
- [ ] **2.3** Verify the Ralph loop keeps Qwen Code retrying a task until it writes a completion marker to the Vault
- [ ] **2.4** Test that Qwen Code can: **Read** a file from `Vault/Needs_Action/`, **Reason** about it, and **Write** a plan to `Vault/Plans/`
- [ ] **2.5** Test autonomous iteration: give Qwen Code a multi-step task and confirm it works until all sub-tasks are marked done (not just one step)
- [ ] **2.6** Review `src/core/retry_handler.py` — confirm retry decorator is wired into long-running agent tasks

---

## PHASE 3 — The Senses (Python Watchers)

### 3A — Filesystem Watcher
- [ ] **3A.1** Start the filesystem watcher:
  ```bash
  bash .agents/skills/filesystem-watcher/scripts/start.sh
  ```
- [ ] **3A.2** Drop a test file into `Vault/Inbox/` (e.g., `echo "hello" > Vault/Inbox/test.txt`)
- [ ] **3A.3** Confirm a metadata file appears in `Vault/Needs_Action/` within polling interval
- [ ] **3A.4** Confirm a log entry is written to `Vault/Logs/<date>.json`
- [ ] **3A.5** Stop the watcher cleanly:
  ```bash
  bash .agents/skills/filesystem-watcher/scripts/stop.sh
  ```

### 3B — Gmail Watcher
- [ ] **3B.1** Complete Gmail OAuth flow — obtain `token.json`
  - Place credentials file at the path defined by `GMAIL_CREDENTIALS_PATH` in `.env`
  - Run the auth script: `python .agents/skills/gmail-watcher/scripts/gmail_auth.py`
- [ ] **3B.2** Start the Gmail watcher:
  ```bash
  bash .agents/skills/gmail-watcher/scripts/start.sh
  ```
- [ ] **3B.3** Send a test email marked **Important** to the monitored inbox
- [ ] **3B.4** Confirm an action file appears in `Vault/Needs_Action/email/`
- [ ] **3B.5** Confirm audit log entry in `Vault/Logs/`
- [ ] **3B.6** Stop the watcher:
  ```bash
  bash .agents/skills/gmail-watcher/scripts/stop.sh
  ```

### 3C — Finance Watcher
- [ ] **3C.1** Create a test CSV with bank transactions and drop it into `Vault/Accounting/Drops/`
  ```csv
  date,description,amount,type
  2026-03-08,Client Payment,5000,credit
  2026-03-08,Office Rent,-2000,debit
  ```
- [ ] **3C.2** Start the finance watcher:
  ```bash
  bash .agents/skills/finance-watcher/scripts/start.sh
  ```
- [ ] **3C.3** Confirm a finance action file appears in `Vault/Needs_Action/finance/`
- [ ] **3C.4** Confirm recurring/subscription patterns are flagged by `src/core/audit_logic.py`
- [ ] **3C.5** Stop the watcher:
  ```bash
  bash .agents/skills/finance-watcher/scripts/stop.sh
  ```

### 3D — Calendar Watcher
- [ ] **3D.1** Complete Google Calendar OAuth flow (same credentials as Gmail)
- [ ] **3D.2** Start the calendar watcher:
  ```bash
  bash .agents/skills/calendar-watcher/scripts/start.sh
  ```
- [ ] **3D.3** Confirm upcoming calendar events create prep task files in `Vault/Needs_Action/calendar/`
- [ ] **3D.4** Stop the watcher:
  ```bash
  bash .agents/skills/calendar-watcher/scripts/stop.sh
  ```

---

## PHASE 4 — The Hands (MCP Servers)

### 4A — Gmail Send MCP
- [ ] **4A.1** Start the Gmail Send MCP server:
  ```bash
  bash .agents/skills/gmail-send-mcp/scripts/start.sh
  ```
- [ ] **4A.2** Run the verify script:
  ```bash
  .venv/bin/python .agents/skills/gmail-send-mcp/scripts/verify.py
  ```
- [ ] **4A.3** Send a real test email (`DRY_RUN=false`) and confirm delivery
- [ ] **4A.4** Confirm `DRY_RUN=true` mode logs intent without sending

### 4B — Social Poster MCP
- [ ] **4B.1** Start the social poster:
  ```bash
  bash .agents/skills/social-poster/scripts/start.sh
  ```
- [ ] **4B.2** Test dry-run for all four platforms (LinkedIn, Facebook, Instagram, X/Twitter)
- [ ] **4B.3** With real tokens in `.env`, test a live post to **one** platform
- [ ] **4B.4** Confirm post content was read from the corresponding `Vault/Schedules/` file
- [ ] **4B.5** Stop the poster:
  ```bash
  bash .agents/skills/social-poster/scripts/stop.sh
  ```

### 4C — LinkedIn Poster (dedicated)
- [ ] **4C.1** Start the LinkedIn poster:
  ```bash
  bash .agents/skills/linkedin-poster/scripts/start.sh
  ```
- [ ] **4C.2** Verify the OAuth access token is valid and not expired
- [ ] **4C.3** Post a test professional update in dry-run mode
- [ ] **4C.4** Stop the poster:
  ```bash
  bash .agents/skills/linkedin-poster/scripts/stop.sh
  ```

### 4D — Odoo Accounting MCP
- [ ] **4D.1** Start the local Odoo stack via Docker Compose:
  ```bash
  docker compose -f docker-compose.odoo.yml up -d
  ```
- [ ] **4D.2** Wait for Odoo to be healthy (port 8069)
- [ ] **4D.3** Run bootstrap script:
  ```bash
  .venv/bin/python .agents/skills/odoo-integration/scripts/bootstrap_accounting.py
  ```
- [ ] **4D.4** Start the Odoo MCP server:
  ```bash
  bash .agents/skills/odoo-integration/scripts/start.sh
  ```
- [ ] **4D.5** Run health check:
  ```bash
  .venv/bin/python .agents/skills/odoo-integration/scripts/verify.py
  ```
- [ ] **4D.6** Test `odoo_health_check`, `odoo_accounting_readiness`, `odoo_list_journals`
- [ ] **4D.7** Test `odoo_ensure_partner` creates a customer record in Odoo
- [ ] **4D.8** Test creating a draft invoice via the MCP and confirm it appears in `Vault/Invoices/`

---

## PHASE 5 — Orchestrator (Reasoning + Workflow Engine)

- [ ] **5.1** Start the orchestrator:
  ```bash
  bash .agents/skills/orchestrator/scripts/start.sh
  ```
- [ ] **5.2** Drop a file into `Vault/Inbox/` and trace the full pipeline:
  - `Inbox/` → `Needs_Action/` (filesystem watcher)
  - `Needs_Action/` → `Plans/` (orchestrator creates plan)
  - `Plans/` → `Pending_Approval/` (orchestrator requests approval)
- [ ] **5.3** **Human-in-the-loop test (Approve):**
  - Move the file from `Pending_Approval/` → `Approved/`
  - Confirm orchestrator executes the approved action and moves result to `Done/`
- [ ] **5.4** **Human-in-the-loop test (Reject):**
  - Move a file from `Pending_Approval/` → `Rejected/`
  - Confirm orchestrator logs the rejection and takes no further action
- [ ] **5.5** Confirm `Vault/Dashboard.md` is updated with the activity timestamp
- [ ] **5.6** Confirm `Vault/Logs/<date>.json` has a structured audit entry
- [ ] **5.7** Stop the orchestrator:
  ```bash
  bash .agents/skills/orchestrator/scripts/stop.sh
  ```

---

## PHASE 6 — CEO Briefing (Executive Autonomy)

- [ ] **6.1** Start the CEO briefing generator:
  ```bash
  bash .agents/skills/ceo-briefing/scripts/start.sh
  ```
- [ ] **6.2** Trigger a manual briefing run (or wait for Monday 07:00 cron)
- [ ] **6.3** Confirm a briefing file is created in `Vault/Briefings/` with naming pattern `YYYY-MM-DD_Monday_Briefing.md`
- [ ] **6.4** Open the briefing in Obsidian — verify it contains:
  - Revenue summary (from finance watcher data)
  - Top bottlenecks / blocked tasks
  - Social media activity recap
  - Pending approvals summary
  - Upcoming calendar events
- [ ] **6.5** Confirm the briefing draft is also staged in `Vault/Pending_Approval/` (requires human approval before email delivery)
- [ ] **6.6** Approve the briefing → confirm it is emailed via Gmail Send MCP

---

## PHASE 7 — Watchdog (Resilience Layer)

- [ ] **7.1** Start the watchdog:
  ```bash
  bash .agents/skills/watchdog/scripts/start.sh
  ```
- [ ] **7.2** Check status of all monitored services:
  ```bash
  bash .agents/skills/watchdog/scripts/status.sh
  ```
- [ ] **7.3** Kill one watcher process manually and confirm watchdog restarts it within the polling interval
- [ ] **7.4** Verify the watchdog itself has a PID file and can be stopped cleanly:
  ```bash
  bash .agents/skills/watchdog/scripts/stop-all.sh
  ```

---

## PHASE 8 — Full Stack Integration Run

- [ ] **8.1** Start ALL services with one command:
  ```bash
  bash .agents/skills/orchestrator/scripts/start_all.sh
  ```
- [ ] **8.2** Confirm all watchers and MCP servers are running (`status.sh`)
- [ ] **8.3** Run the full end-to-end smoke test:
  1. Drop a finance CSV → `Vault/Accounting/Drops/`
  2. Send an important email to the monitored inbox
  3. Drop a text file → `Vault/Inbox/`
  4. Approve one pending item → confirm it moves to `Done/`
  5. Reject one pending item → confirm rejection is logged
- [ ] **8.4** Verify `Vault/Dashboard.md` reflects all activity
- [ ] **8.5** Stop ALL services:
  ```bash
  bash .agents/skills/orchestrator/scripts/stop_all.sh
  ```

---

## PHASE 9 — Cron / Scheduling (Automation at Scale)

- [ ] **9.1** Install cron jobs for scheduled tasks:
  ```bash
  bash .agents/skills/orchestrator/scripts/install_cron.sh
  ```
- [ ] **9.2** Verify cron entries are present (`crontab -l`):
  - LinkedIn post: Mon/Wed/Fri at 09:00
  - Facebook post: Tue/Thu at 10:00
  - Instagram post: Tue/Thu at 11:00
  - X (Twitter) post: Mon/Wed/Fri at 12:00
  - CEO briefing: Monday at 07:00
- [ ] **9.3** Confirm schedule config files exist in `Vault/Schedules/`:
  - `linkedin_post.md`
  - `facebook_post.md`
  - `instagram_post.md`
  - `twitter_post.md`
  - `weekly_ceo_briefing.md`
- [ ] **9.4** Edit a schedule file in Obsidian and confirm the next run picks up the new content

---

## PHASE 10 — Docker Deployment (Optional / Production)

- [ ] **10.1** Build the Docker image:
  ```bash
  docker build -t personal-ai-employee .
  ```
- [ ] **10.2** Confirm the Dockerfile copies all required source files and installs dependencies
- [ ] **10.3** Run the container with Vault mounted:
  ```bash
  docker run --name personal-ai-employee \
    --env-file .env \
    -e VAULT_PATH=/app/Vault \
    -v "$(pwd)/Vault:/app/Vault" \
    personal-ai-employee
  ```
- [ ] **10.4** Drop a file into `Vault/Inbox/` from the host and confirm the container processes it (Vault is shared)
- [ ] **10.5** Stop the container:
  ```bash
  docker stop personal-ai-employee
  ```
- [ ] **10.6** (Optional) Run the full Odoo stack with Docker Compose:
  ```bash
  docker compose -f docker-compose.odoo.yml up -d
  ```

---

## PHASE 11 — Security & Safety Check

- [ ] **11.1** Confirm `.env` is never committed to git (`git status` should not show `.env`)
- [ ] **11.2** Confirm all API tokens are loaded from environment variables, never hard-coded in source
- [ ] **11.3** Confirm `DRY_RUN=true` is the default for all external actions (email, social, accounting)
- [ ] **11.4** Confirm human-in-the-loop approval is required before any irreversible action (email send, invoice creation, social post)
- [ ] **11.5** Review `src/core/audit_logger.py` — all agent actions must be logged with timestamp, actor, and outcome
- [ ] **11.6** Confirm no personally identifiable information (PII) is written to `Vault/Logs/` in plaintext beyond what is necessary
- [ ] **11.7** Confirm OAuth token files (`token.json`) are excluded from git and stored securely

---

## PHASE 12 — Hackathon Demo Preparation

- [ ] **12.1** Prepare a 2-minute live demo script covering the full pipeline (file drop → plan → approval → done)
- [ ] **12.2** Open Obsidian on a second monitor showing `Vault/Dashboard.md` during demo
- [ ] **12.3** Have a pre-populated finance CSV ready to show the CEO briefing generation
- [ ] **12.4** Run a final full-stack smoke test the night before (`start_all.sh` + all 5 smoke test steps)
- [ ] **12.5** Prepare a one-slide architecture diagram showing Brain → Memory → Senses → Hands
- [ ] **12.6** Be ready to explain the **Ralph Wiggum Stop Hook** — why it prevents "lazy agent" behavior
- [ ] **12.7** Be ready to explain the **human-in-the-loop approval** workflow and why it matters for safety

---

## Quick Verification Commands (Run Anytime)

```bash
# Environment
source .venv/bin/activate && python -c "import google.auth, requests; print('deps OK')"

# Vault write test
echo "test $(date)" >> Vault/Inbox/test-$(date +%s).txt

# Check all watchers are running
bash .agents/skills/watchdog/scripts/status.sh

# View recent audit log
cat Vault/Logs/$(date +%Y-%m-%d).json | python3 -m json.tool | tail -40

# View dashboard
cat Vault/Dashboard.md
```

---

## Done Criteria

| Area | Done When |
|---|---|
| Vault (Obsidian) | Qwen Code can read & write markdown files and changes appear in Obsidian |
| Filesystem Watcher | File dropped in `Inbox/` → appears in `Needs_Action/` automatically |
| Gmail Watcher | Important email → action file in `Needs_Action/email/` |
| Finance Watcher | CSV drop → finance action file + subscription pattern detection |
| Orchestrator | `Needs_Action/` → `Plans/` → `Pending_Approval/` → `Done/` full cycle |
| Ralph Loop | Qwen Code iterates autonomously until task completion marker is written |
| CEO Briefing | Monday briefing MD file generated with revenue + bottleneck summary |
| Social Poster | Dry-run posts succeed for all 4 platforms; at least 1 live post confirmed |
| Gmail Send MCP | Dry-run and 1 real email delivery confirmed |
| Odoo MCP | Health check passes; draft invoice created and logged |
| Watchdog | Killed process is auto-restarted within polling interval |
| Security | No tokens in git; DRY_RUN default; all actions logged |
| Full Stack | `start_all.sh` → full smoke test → `stop_all.sh` passes cleanly |
