# Run Commands (Working)

Yeh file project ke tested/runnable commands ka quick reference hai.

## 1) Environment Setup

```bash
cd /home/abdul-matten/Desktop/Personal-AI-Employee
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Agar venv pehle se bana hua hai:

```bash
cd /home/abdul-matten/Desktop/Personal-AI-Employee
source .venv/bin/activate
```

## 2) Gmail Send MCP

Start:

```bash
bash .agents/skills/gmail-send-mcp/scripts/start.sh
```

Verify:

```bash
.venv/bin/python .agents/skills/gmail-send-mcp/scripts/verify.py
```

Stop:

```bash
bash .agents/skills/gmail-send-mcp/scripts/stop.sh
```

### Real test email bhejne ka command

```bash
DRY_RUN=false .venv/bin/python - <<'PY'
import os
import importlib.util
from dotenv import load_dotenv

load_dotenv(dotenv_path='.env')

script_path = '.agents/skills/gmail-send-mcp/scripts/gmail_send_mcp.py'
spec = importlib.util.spec_from_file_location('gmail_send_mcp', script_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

to_addr = os.getenv('RECIPIENT_EMAIL') or os.getenv('SENDER_EMAIL') or os.getenv('GMAIL_DELEGATE_EMAIL')
subject = 'Test Email'
body = 'Test email from Personal-AI-Employee.'
print(mod.send_email(to_addr, subject, body))
PY
```

## 3) Gmail Watcher

OAuth setup (one-time):

```bash
.venv/bin/python .agents/skills/gmail-watcher/scripts/gmail_oauth_setup.py
```

Start:

```bash
bash .agents/skills/gmail-watcher/scripts/start.sh
```

Verify:

```bash
.venv/bin/python .agents/skills/gmail-watcher/scripts/verify.py
```

Stop:

```bash
bash .agents/skills/gmail-watcher/scripts/stop.sh
```

## 4) Calendar Watcher

OAuth setup (one-time):

```bash
.venv/bin/python .agents/skills/calendar-watcher/scripts/calendar_oauth_setup.py
```

Start:

```bash
bash .agents/skills/calendar-watcher/scripts/start.sh
```

Verify:

```bash
.venv/bin/python .agents/skills/calendar-watcher/scripts/verify.py
```

Stop:

```bash
bash .agents/skills/calendar-watcher/scripts/stop.sh
```

### Calendar me event add karne ka command (manual API call)

Note: calendar-watcher skill khud se new event create nahi karta; yeh command direct Google Calendar API se event insert karta hai.

```bash
.venv/bin/python - <<'PY'
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv('.env')

token_path = os.getenv('GOOGLE_CALENDAR_TOKEN_PATH')
calendar_id = os.getenv('CALENDAR_ID', 'primary')
creds = Credentials.from_authorized_user_file(token_path)
service = build('calendar', 'v3', credentials=creds)

start = datetime.now(timezone.utc) + timedelta(hours=2)
end = start + timedelta(hours=1)

body = {
    'summary': 'Test Event (Personal AI Employee)',
    'description': 'Auto-created test event',
    'start': {'dateTime': start.isoformat()},
    'end': {'dateTime': end.isoformat()},
}

event = service.events().insert(calendarId=calendar_id, body=body).execute()
print('Event created:', event.get('htmlLink'))
PY
```

## 5) Core Stack Commands

MVP start:

```bash
bash .agents/skills/filesystem-watcher/scripts/start.sh
bash .agents/skills/orchestrator/scripts/start.sh
```

MVP stop:

```bash
bash .agents/skills/filesystem-watcher/scripts/stop.sh
bash .agents/skills/orchestrator/scripts/stop.sh
```

Full stack start:

```bash
bash .agents/skills/orchestrator/scripts/start_all.sh
```

Full stack stop:

```bash
bash .agents/skills/orchestrator/scripts/stop_all.sh
```

## 6) Other Working Skills

Finance watcher:

```bash
bash .agents/skills/finance-watcher/scripts/start.sh
.venv/bin/python .agents/skills/finance-watcher/scripts/verify.py
bash .agents/skills/finance-watcher/scripts/stop.sh
```

Social poster:

```bash
bash .agents/skills/social-poster/scripts/start.sh
.venv/bin/python .agents/skills/social-poster/scripts/verify.py
bash .agents/skills/social-poster/scripts/stop.sh
```

CEO briefing:

```bash
bash .agents/skills/ceo-briefing/scripts/start.sh
.venv/bin/python .agents/skills/ceo-briefing/scripts/verify.py
bash .agents/skills/ceo-briefing/scripts/stop.sh
```

LinkedIn poster:

```bash
.venv/bin/python .agents/skills/linkedin-poster/scripts/linkedin_oauth_setup.py
bash .agents/skills/linkedin-poster/scripts/start.sh
.venv/bin/python .agents/skills/linkedin-poster/scripts/verify.py
bash .agents/skills/linkedin-poster/scripts/stop.sh
```

Watchdog:

```bash
bash .agents/skills/watchdog/scripts/start.sh
bash .agents/skills/watchdog/scripts/status.sh
bash .agents/skills/watchdog/scripts/stop.sh
bash .agents/skills/watchdog/scripts/stop-all.sh
```

Odoo integration:

```bash
bash .agents/skills/odoo-integration/scripts/start-local-odoo.sh
bash .agents/skills/odoo-integration/scripts/start-server.sh
.venv/bin/python .agents/skills/odoo-integration/scripts/verify.py
bash .agents/skills/odoo-integration/scripts/stop-server.sh
bash .agents/skills/odoo-integration/scripts/stop-local-odoo.sh
```

Ralph loop:

```bash
.venv/bin/python .agents/skills/ralph-loop/scripts/ralph_loop.py \
  --command ".venv/bin/python .agents/skills/orchestrator/scripts/orchestrator.py" \
  --done-file "Vault/Done/TASK_COMPLETE.md" \
  --max-iterations 10
```
