```skill
---
name: filesystem-watcher
description: Monitors local file drops and creates actionable markdown files in the vault.
---
```

# File System Watcher

Watch local file drops and mirror them into `/Needs_Action` with metadata.

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

## Behavior

- Watches `Vault/Inbox`
- Copies new files into `Vault/Needs_Action` with `FILE_` prefix
- Creates metadata `.md` sidecar file with file size and source name

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Not detecting files | Ensure `Vault/Inbox` exists and watcher is running |
| Permission denied | Check file permissions for vault folders |
