from __future__ import annotations

import os
import xmlrpc.client
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.retry_handler import TransientError, with_retry


@dataclass
class OdooConfig:
    url: str
    db: str
    user: str
    password: str


class OdooClient:
    def __init__(self, config: OdooConfig):
        self.config = config
        self.common = xmlrpc.client.ServerProxy(f"{config.url}/xmlrpc/2/common")
        self.uid = self.common.authenticate(config.db, config.user, config.password, {})
        self.models = xmlrpc.client.ServerProxy(f"{config.url}/xmlrpc/2/object")

    @with_retry(max_attempts=3, base_delay=1, max_delay=8)
    def _execute(self, model: str, method: str, args: list, kwargs: dict | None = None):
        try:
            return self.models.execute_kw(
                self.config.db,
                self.uid,
                self.config.password,
                model,
                method,
                args,
                kwargs or {},
            )
        except xmlrpc.client.ProtocolError as exc:
            raise TransientError(str(exc)) from exc

    def list_partners(self, limit: int = 10):
        return self._execute(
            "res.partner",
            "search_read",
            [[]],
            {"fields": ["name", "email"], "limit": limit},
        )

    def create_draft_invoice(
        self,
        partner_id: int,
        lines: list[dict],
        move_type: str = "out_invoice",
        currency_id: int | None = None,
        narration: str | None = None,
    ) -> int:
        payload: dict = {
            "partner_id": partner_id,
            "move_type": move_type,
            "invoice_line_ids": [
                [
                    0,
                    0,
                    {
                        "name": line.get("name", "Service"),
                        "quantity": float(line.get("quantity", 1.0)),
                        "price_unit": float(line.get("price_unit", 0.0)),
                    },
                ]
                for line in lines
            ],
        }
        if currency_id:
            payload["currency_id"] = currency_id
        if narration:
            payload["narration"] = narration

        invoice_id = self._execute("account.move", "create", [[payload]])
        return int(invoice_id)

    def list_draft_invoices(self, limit: int = 20):
        return self._execute(
            "account.move",
            "search_read",
            [[("move_type", "=", "out_invoice"), ("state", "=", "draft")]],
            {
                "fields": ["id", "name", "invoice_date", "amount_total", "partner_id"],
                "limit": limit,
                "order": "id desc",
            },
        )

    def create_draft_payment(
        self,
        partner_id: int,
        amount: float,
        payment_type: str = "outbound",
        partner_type: str = "supplier",
        memo: str | None = None,
    ) -> int:
        payload: dict = {
            "partner_id": partner_id,
            "amount": float(amount),
            "payment_type": payment_type,
            "partner_type": partner_type,
        }
        if memo:
            payload["ref"] = memo

        payment_id = self._execute("account.payment", "create", [[payload]])
        return int(payment_id)


def from_env() -> OdooClient:
    cfg = OdooConfig(
        url=os.getenv("ODOO_URL", "http://localhost:8069"),
        db=os.getenv("ODOO_DB", "odoo_db"),
        user=os.getenv("ODOO_USER", "admin"),
        password=os.getenv("ODOO_PASSWORD", "admin"),
    )
    return OdooClient(cfg)
