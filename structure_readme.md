# Personal AI Employee — Project Structure & Usage Guide

## Project Overview

Yeh ek **AI-powered personal employee** system hai jo aapke emails, files, calendar, finances, aur social media ko autonomously manage karta hai. Har cheez ek local `Vault/` folder ke through flow hoti hai — human-in-the-loop approval ke saath.

---

## Complete Project Structure

```
Personal-AI-Employee/
│
├── .agents/                        # All AI agent skills (plugins)
│   └── skills/
│       ├── browsing-with-playwright/   # Browser automation (Playwright MCP)
│       ├── calendar-watcher/           # Google Calendar monitoring
│       ├── ceo-briefing/               # Weekly Monday CEO briefing generation
│       ├── filesystem-watcher/         # Local file drop watcher (Vault/Inbox)
│       ├── finance-watcher/            # CSV-based finance monitoring
│       ├── gmail-send-mcp/             # Gmail send (MCP-style server)
│       ├── gmail-watcher/              # Gmail inbox monitoring (OAuth)
│       ├── linkedin-poster/            # LinkedIn post publisher
│       ├── odoo-integration/           # Odoo 19 JSON-RPC accounting integration
│       ├── orchestrator/               # Central brain — plans & actions
│       ├── qwen-agent/                 # Qwen AI model agent
│       ├── ralph-loop/                 # Persistence loop utility
│       ├── social-poster/              # Facebook / Instagram / X posting
│       └── watchdog/                   # Service health monitor & auto-restart
│
├── src/                            # Core Python modules
│   └── core/
│       ├── __init__.py
│       ├── audit_logger.py             # JSON audit log writer (Vault/Logs/)
│       ├── audit_logic.py              # Audit decision logic
│       ├── base_watcher.py             # Base class for all watchers
│       ├── config.py                   # Centralized config / env loader
│       ├── gmail_auth.py               # Gmail OAuth helper
│       └── retry_handler.py            # Retry/backoff utility
│
├── Vault/                          # Data hub — all task flow lives here
│   ├── Inbox/                          # Drop files here → triggers processing
│   │   └── Pending_Approval/           # Sub-categories awaiting approval
│   │       ├── calendar/
│   │       ├── email/
│   │       ├── finance/
│   │       ├── general/
│   │       └── social/
│   ├── Needs_Action/                   # Items requiring human attention
│   │   ├── calendar/
│   │   ├── email/
│   │   ├── finance/
│   │   └── social/
│   ├── Plans/                          # AI-generated action plans
│   │   ├── calendar/
│   │   ├── email/
│   │   ├── finance/
│   │   ├── general/
│   │   └── social/
│   ├── Pending_Approval/               # Drafts awaiting human approve/reject
│   │   ├── email/
│   │   └── general/
│   ├── Approved/                       # Human-approved items → executed
│   ├── Rejected/                       # Human-rejected items → archived
│   ├── Done/                           # Completed/processed tasks
│   ├── Logs/                           # JSON audit logs (per day)
│   ├── Briefings/                      # CEO briefing outputs
│   ├── Schedules/                      # Scheduled posting configs
│   │   ├── facebook_post.md
│   │   ├── instagram_post.md
│   │   ├── linkedin_post.md
│   │   ├── twitter_post.md
│   │   └── weekly_ceo_briefing.md
│   ├── Invoices/                       # Invoice files
│   ├── Accounting/                     # Accounting data / drops
│   ├── In_Progress/                    # Currently being processed
│   ├── Active_Project/                 # Active project notes
│   ├── Updates/                        # Update notifications
│   ├── Business_Goals.md               # Business goals reference
│   ├── Company_Handbook.md             # Company handbook reference
│   └── Dashboard.md                    # Overview dashboard
│
├── docker/                         # Docker support files
│   └── entrypoint.sh                  # Container entrypoint (starts watcher + orchestrator)
│
├── odoo/                           # Odoo custom addons
│   └── addons/
│
├── Dockerfile                      # App Docker image (Python 3.11-slim)
├── docker-compose.odoo.yml         # Odoo 19 + PostgreSQL compose stack
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables (API keys, tokens, paths)
├── .dockerignore                   # Docker build exclusions
├── .gitignore                      # Git exclusions
├── skills-lock.json                # Skill versions lock file
├── README.md                       # Main project readme
├── RUN_WORKING_COMMANDS.md         # Tested run commands reference
├── HACKATHON_CHECKLIST.md          # Hackathon feature checklist
├── IMPLEMENTATION_SHORT.md         # Implementation summary
└── QWEN.md                        # Qwen model notes
```

---

## Architecture Flow

```
   ┌──────────────┐     ┌───────────────┐     ┌────────────────┐
   │  Gmail Watch  │     │  File Watcher  │     │ Calendar Watch │
   │  Finance CSV  │     │  (Vault/Inbox) │     │  Social Sched  │
   └──────┬───────┘     └───────┬────────┘     └───────┬────────┘
          │                     │                       │
          └─────────────┬───────┘───────────────────────┘
                        ▼
               ┌─────────────────┐
               │   Orchestrator   │  ← Central brain
               │  (creates plans) │
               └────────┬────────┘
                        ▼
               ┌─────────────────┐
               │ Pending_Approval │  ← Human reviews here
               └────────┬────────┘
                   ┌────┴────┐
                   ▼         ▼
              Approved    Rejected
                   │
                   ▼
            ┌────────────┐
            │   Actions   │  (send email, post social, create invoice)
            └────────────┘
                   │
                   ▼
               Vault/Done
```

---

## How to Run

### Prerequisites

- Linux / macOS
- Python 3.11+
- Docker & Docker Compose (for containerized run)
- `.env` file configured (API keys, OAuth tokens, vault path)

---

### Option 1: Run with Docker (Recommended)

**Build the image:**

```bash
docker build -t personal-ai-employee .
```

**Run the container:**

```bash
docker run -d --name personal-ai-employee \
  --env-file .env \
  -e VAULT_PATH=/app/Vault \
  -v "$(pwd)/Vault:/app/Vault" \
  personal-ai-employee
```

**Useful commands:**

```bash
# Check status
docker ps -a | grep personal-ai-employee

# View live logs
docker logs -f personal-ai-employee

# Stop
docker stop personal-ai-employee

# Start again
docker start personal-ai-employee

# Remove & recreate
docker rm -f personal-ai-employee
```

> **Note:** Agar `PermissionError` aaye `Vault/Logs/` par, to pehle root-owned files delete karein:
> ```bash
> sudo find Vault -user root -exec rm -f {} +
> ```

---

### Option 2: Run with Docker Compose (Odoo Stack)

```bash
# Start Odoo + PostgreSQL
docker compose -f docker-compose.odoo.yml up -d

# Stop Odoo stack
docker compose -f docker-compose.odoo.yml down
```

Odoo UI: `http://localhost:8069`

---

### Option 3: Run Locally (without Docker)

**Setup environment:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Start MVP stack (filesystem watcher + orchestrator):**

```bash
bash .agents/skills/filesystem-watcher/scripts/start.sh
bash .agents/skills/orchestrator/scripts/start.sh
```

**Start full stack (all services):**

```bash
bash .agents/skills/orchestrator/scripts/start_all.sh
```

**Stop all:**

```bash
bash .agents/skills/orchestrator/scripts/stop_all.sh
```

---

## Individual Skills — Start / Verify / Stop

| Skill | Start | Verify | Stop |
|---|---|---|---|
| Filesystem Watcher | `bash .agents/skills/filesystem-watcher/scripts/start.sh` | — | `bash .agents/skills/filesystem-watcher/scripts/stop.sh` |
| Orchestrator | `bash .agents/skills/orchestrator/scripts/start.sh` | — | `bash .agents/skills/orchestrator/scripts/stop.sh` |
| Gmail Watcher | `bash .agents/skills/gmail-watcher/scripts/start.sh` | `.venv/bin/python .agents/skills/gmail-watcher/scripts/verify.py` | `bash .agents/skills/gmail-watcher/scripts/stop.sh` |
| Gmail Send MCP | `bash .agents/skills/gmail-send-mcp/scripts/start.sh` | `.venv/bin/python .agents/skills/gmail-send-mcp/scripts/verify.py` | `bash .agents/skills/gmail-send-mcp/scripts/stop.sh` |
| Calendar Watcher | `bash .agents/skills/calendar-watcher/scripts/start.sh` | `.venv/bin/python .agents/skills/calendar-watcher/scripts/verify.py` | `bash .agents/skills/calendar-watcher/scripts/stop.sh` |
| Finance Watcher | `bash .agents/skills/finance-watcher/scripts/start.sh` | `.venv/bin/python .agents/skills/finance-watcher/scripts/verify.py` | `bash .agents/skills/finance-watcher/scripts/stop.sh` |
| Social Poster | `bash .agents/skills/social-poster/scripts/start.sh` | `.venv/bin/python .agents/skills/social-poster/scripts/verify.py` | `bash .agents/skills/social-poster/scripts/stop.sh` |
| LinkedIn Poster | `bash .agents/skills/linkedin-poster/scripts/start.sh` | `.venv/bin/python .agents/skills/linkedin-poster/scripts/verify.py` | `bash .agents/skills/linkedin-poster/scripts/stop.sh` |
| CEO Briefing | `bash .agents/skills/ceo-briefing/scripts/start.sh` | `.venv/bin/python .agents/skills/ceo-briefing/scripts/verify.py` | `bash .agents/skills/ceo-briefing/scripts/stop.sh` |
| Odoo Integration | `bash .agents/skills/odoo-integration/scripts/start-server.sh` | `.venv/bin/python .agents/skills/odoo-integration/scripts/verify.py` | `bash .agents/skills/odoo-integration/scripts/stop-server.sh` |
| Watchdog | `bash .agents/skills/watchdog/scripts/start.sh` | `bash .agents/skills/watchdog/scripts/status.sh` | `bash .agents/skills/watchdog/scripts/stop.sh` |

---

## OAuth Setup (One-Time)

```bash
# Gmail (read + send)
.venv/bin/python .agents/skills/gmail-watcher/scripts/gmail_oauth_setup.py

# Google Calendar
.venv/bin/python .agents/skills/calendar-watcher/scripts/calendar_oauth_setup.py

# LinkedIn
.venv/bin/python .agents/skills/linkedin-poster/scripts/linkedin_oauth_setup.py
```

---

## How to Use (Workflow)

1. **File drop:** Koi bhi file `Vault/Inbox/` mein daalo — watcher detect karega.
2. **Plan generation:** Orchestrator automatically plan banayega (`Vault/Plans/`).
3. **Review:** Draft actions `Vault/Pending_Approval/` mein aayengi.
4. **Approve/Reject:** File ko `Vault/Approved/` ya `Vault/Rejected/` mein move karo.
5. **Execution:** Approved actions execute ho jayengi (email send, social post, invoice create).
6. **Done:** Completed items `Vault/Done/` mein archive ho jayengi.
7. **Logs:** Har action ka JSON log `Vault/Logs/` mein milega.

---

## Key Environment Variables (`.env`)

| Variable | Purpose |
|---|---|
| `VAULT_PATH` | Path to Vault folder (default: `./Vault`) |
| `DRY_RUN` | `true` = no real actions, `false` = live mode |
| `SENDER_EMAIL` | Gmail sender address |
| `RECIPIENT_EMAIL` | Default recipient email |
| `GOOGLE_CALENDAR_TOKEN_PATH` | Path to Calendar OAuth token |
| `CALENDAR_ID` | Google Calendar ID (default: `primary`) |
| `ODOO_URL` | Odoo server URL (e.g., `http://localhost:8069`) |
| `ODOO_DB` | Odoo database name |
| `ODOO_USER` | Odoo username |
| `ODOO_PASSWORD` | Odoo password |

---

## Dependencies

```
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
google-api-python-client>=2.0.0
watchdog>=4.0.0
python-dotenv>=1.0.0
requests>=2.32.0
mcp[cli]>=1.0.0
schedule>=1.2.0
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `PermissionError` on `Vault/Logs/` | `sudo find Vault -user root -exec rm -f {} +` then restart |
| `docker run` Exit Code 125 | `docker rm -f personal-ai-employee` then run again |
| OAuth token expired | Re-run the OAuth setup script for that service |
| Container exits immediately | Check `docker logs personal-ai-employee` for traceback |
| Port 8069 already in use | `docker compose -f docker-compose.odoo.yml down` first |

---

## Logs Location

- App logs: `/tmp/filesystem-watcher.log`, `/tmp/orchestrator.log`, `/tmp/watchdog.log`
- Audit logs: `Vault/Logs/YYYY-MM-DD.json`
