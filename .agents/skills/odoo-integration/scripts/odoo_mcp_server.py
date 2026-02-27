import json
import os
import sys
import traceback

from odoo_client import from_env


def main() -> None:
    client = None

    def get_client():
        nonlocal client
        if client is None:
            client = from_env()
        return client

    dry_run = os.getenv("DRY_RUN", "true").strip().lower() in {"1", "true", "yes", "on"}

    for raw in sys.stdin:
        request = {}
        try:
            request = json.loads(raw)
            method = request.get("method")
            params = request.get("params") or {}

            if method == "odoo_list_partners":
                result = get_client().list_partners(limit=int(params.get("limit", 10)))
                response = {"id": request.get("id"), "result": result}

            elif method == "odoo_list_draft_invoices":
                result = get_client().list_draft_invoices(limit=int(params.get("limit", 20)))
                response = {"id": request.get("id"), "result": result}

            elif method == "odoo_create_draft_invoice":
                if dry_run:
                    response = {
                        "id": request.get("id"),
                        "result": {
                            "status": "dry_run",
                            "message": "Would create Odoo draft invoice",
                            "params": params,
                        },
                    }
                else:
                    invoice_id = get_client().create_draft_invoice(
                        partner_id=int(params["partner_id"]),
                        lines=params.get("lines", []),
                        move_type=params.get("move_type", "out_invoice"),
                        currency_id=params.get("currency_id"),
                        narration=params.get("narration"),
                    )
                    response = {
                        "id": request.get("id"),
                        "result": {"status": "created", "invoice_id": invoice_id},
                    }

            elif method == "odoo_create_draft_payment":
                if dry_run:
                    response = {
                        "id": request.get("id"),
                        "result": {
                            "status": "dry_run",
                            "message": "Would create Odoo draft payment",
                            "params": params,
                        },
                    }
                else:
                    payment_id = get_client().create_draft_payment(
                        partner_id=int(params["partner_id"]),
                        amount=float(params["amount"]),
                        payment_type=params.get("payment_type", "outbound"),
                        partner_type=params.get("partner_type", "supplier"),
                        memo=params.get("memo"),
                    )
                    response = {
                        "id": request.get("id"),
                        "result": {"status": "created", "payment_id": payment_id},
                    }

            else:
                response = {
                    "id": request.get("id"),
                    "error": {"message": f"Unsupported method: {method}"},
                }

        except Exception as exc:
            response = {
                "id": request.get("id"),
                "error": {
                    "message": str(exc),
                    "trace": traceback.format_exc(limit=2),
                },
            }

        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
