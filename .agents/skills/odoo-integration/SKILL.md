```skill
---
name: odoo-integration
description: Odoo 19 integration skeleton with draft-first, approval-oriented operations.
---
```

# Odoo Integration

Connects to Odoo via XML-RPC and provides draft-first finance operations.

## Start Server
```bash
bash scripts/start-server.sh
```

## Stop Server
```bash
bash scripts/stop-server.sh
```

## Verify
```bash
python3 scripts/verify.py
```

## Notes
- Configure `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD` in `.env`
- This is a safe skeleton and does not auto-post financial entries
