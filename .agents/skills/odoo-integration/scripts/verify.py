from odoo_client import from_env


try:
    partners = from_env().list_partners(limit=1)
    print(f"✓ odoo reachable (sample partners: {len(partners)})")
except Exception as exc:
    print(f"✗ odoo verify failed: {exc}")
    raise SystemExit(1)
