```skill
---
name: calendar-watcher
description: Polls Google Calendar and creates event preparation action files.
---
```

# Calendar Watcher

Monitors upcoming events and writes actionable items into `/Needs_Action`.

## Server Lifecycle

### Start
```bash
bash scripts/start.sh
```

### Stop
```bash
bash scripts/stop.sh
```

### Verify
```bash
python3 scripts/verify.py
```
