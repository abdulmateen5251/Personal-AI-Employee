```skill
---
name: odoo-integration
description: Odoo 19 integration with draft-first invoice/payment operations and approval-oriented execution.
---
```

# Odoo Integration

Connects to Odoo via XML-RPC and provides draft-first finance operations.

## Available Methods
- `odoo_list_partners`
- `odoo_list_draft_invoices`
- `odoo_create_draft_invoice`
- `odoo_create_draft_payment`

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
- `DRY_RUN=true` keeps create methods in simulation mode
- No auto-posting of financial entries is performed
