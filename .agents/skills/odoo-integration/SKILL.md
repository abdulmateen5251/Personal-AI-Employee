```skill
---
name: odoo-integration
description: Odoo 19 integration with draft-first invoice/payment operations and approval-oriented execution.
---
```

# Odoo Integration

Connects to Odoo 19+ via JSON-RPC and provides draft-first finance operations.

## Local Self-Hosted Odoo (Community)
```bash
bash scripts/start-local-odoo.sh
```

Then open `http://localhost:8069` and create/select your local database.

To stop local Odoo:

```bash
bash scripts/stop-local-odoo.sh
```

## Available Methods
- `odoo_health_check`
- `odoo_accounting_readiness`
- `odoo_list_journals`
- `odoo_list_accounts`
- `odoo_ensure_partner`
- `odoo_list_partners`
- `odoo_list_draft_invoices`
- `odoo_create_draft_invoice`
- `odoo_create_draft_payment`

## Bootstrap Readiness
```bash
python3 scripts/bootstrap_accounting.py --ensure-partner-name "Acme LLC"
```

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
- JSON-RPC endpoint used by this integration: `/jsonrpc`
