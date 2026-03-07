from __future__ import annotations

import argparse
import json

from odoo_client import from_env


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap and validate Odoo accounting readiness")
    parser.add_argument("--ensure-partner-name", default="", help="Create/find business partner by name")
    parser.add_argument("--ensure-partner-email", default="", help="Optional partner email")
    args = parser.parse_args()

    client = from_env()

    summary: dict = {
        "health": client.health_check(),
        "readiness": client.accounting_readiness(),
        "sample_journals": client.list_journals(limit=5),
        "sample_accounts": client.list_accounts(limit=5),
    }

    if args.ensure_partner_name.strip():
        summary["partner"] = client.ensure_partner(
            name=args.ensure_partner_name.strip(),
            email=args.ensure_partner_email.strip() or None,
            is_company=True,
        )

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
