from __future__ import annotations

import os
from itertools import count
from dataclasses import dataclass
from pathlib import Path
import sys

import requests

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
        self._request_counter = count(1)
        self._session = requests.Session()
        self._jsonrpc_url = f"{config.url.rstrip('/')}/jsonrpc"
        self.uid = self._login()

    def _jsonrpc(self, service: str, method: str, *args):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": service,
                "method": method,
                "args": list(args),
            },
            "id": next(self._request_counter),
        }
        try:
            response = self._session.post(self._jsonrpc_url, json=payload, timeout=20)
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise TransientError(str(exc)) from exc

        if "error" in body:
            message = body["error"].get("message", "Odoo JSON-RPC call failed")
            data = body["error"].get("data", {})
            details = data.get("message")
            raise RuntimeError(f"{message}: {details}" if details else message)

        return body.get("result")

    def _login(self) -> int:
        uid = self._jsonrpc(
            "common",
            "login",
            self.config.db,
            self.config.user,
            self.config.password,
        )
        if not uid:
            raise RuntimeError("Failed to authenticate to Odoo; check ODOO_* credentials")
        return int(uid)

    @with_retry(max_attempts=3, base_delay=1, max_delay=8)
    def _execute(self, model: str, method: str, args: list, kwargs: dict | None = None):
        return self._jsonrpc(
            "object",
            "execute_kw",
            self.config.db,
            self.uid,
            self.config.password,
            model,
            method,
            args,
            kwargs or {},
        )

    def list_partners(self, limit: int = 10):
        return self._execute(
            "res.partner",
            "search_read",
            [[]],
            {"fields": ["name", "email"], "limit": limit},
        )

    def health_check(self) -> dict:
        user = self._execute(
            "res.users",
            "search_read",
            [[("id", "=", self.uid)]],
            {"fields": ["id", "name", "login"], "limit": 1},
        )
        return {
            "status": "ok",
            "url": self.config.url,
            "db": self.config.db,
            "uid": self.uid,
            "user": user[0] if user else None,
        }

    def list_journals(self, limit: int = 20):
        return self._execute(
            "account.journal",
            "search_read",
            [[]],
            {
                "fields": ["id", "name", "code", "type", "company_id"],
                "limit": limit,
                "order": "id asc",
            },
        )

    def list_accounts(self, limit: int = 20):
        domain = self._account_domain_for_active_records()
        return self._execute(
            "account.account",
            "search_read",
            [domain],
            {
                "fields": ["id", "code", "name", "account_type", "company_ids"],
                "limit": limit,
                "order": "code asc",
            },
        )

    def _account_domain_for_active_records(self) -> list:
        # Odoo versions/images can differ: some use `deprecated`, others use `active`.
        try:
            self._execute("account.account", "search_count", [[("deprecated", "=", False)]])
            return [("deprecated", "=", False)]
        except RuntimeError as exc:
            if "Invalid field account.account.deprecated" not in str(exc):
                raise

        try:
            self._execute("account.account", "search_count", [[("active", "=", True)]])
            return [("active", "=", True)]
        except RuntimeError:
            return []

    def ensure_partner(self, name: str, email: str | None = None, is_company: bool = True) -> dict:
        if not name.strip():
            raise ValueError("name is required")

        domain = [[("name", "=", name.strip())]]
        if email:
            domain = [["|", ("name", "=", name.strip()), ("email", "=", email.strip())]]

        found = self._execute(
            "res.partner",
            "search_read",
            domain,
            {"fields": ["id", "name", "email", "is_company"], "limit": 1},
        )
        if found:
            return {"status": "exists", "partner": found[0]}

        payload: dict = {"name": name.strip(), "is_company": bool(is_company)}
        if email:
            payload["email"] = email.strip()

        raw_partner_id = self._execute("res.partner", "create", [[payload]])
        partner_id = int(raw_partner_id[0]) if isinstance(raw_partner_id, list) else int(raw_partner_id)
        partner = self._execute(
            "res.partner",
            "search_read",
            [[("id", "=", partner_id)]],
            {"fields": ["id", "name", "email", "is_company"], "limit": 1},
        )
        return {"status": "created", "partner": partner[0] if partner else {"id": partner_id}}

    def accounting_readiness(self) -> dict:
        journals = self._execute("account.journal", "search_count", [[]])
        accounts = self._execute("account.account", "search_count", [self._account_domain_for_active_records()])
        bank_journals = self._execute(
            "account.journal",
            "search_count",
            [[("type", "=", "bank")]],
        )
        sale_journals = self._execute(
            "account.journal",
            "search_count",
            [[("type", "=", "sale")]],
        )
        purchase_journals = self._execute(
            "account.journal",
            "search_count",
            [[("type", "=", "purchase")]],
        )
        suggestions: list[str] = []
        if int(accounts) == 0:
            suggestions.append("Configure chart of accounts from Accounting settings")
        if int(sale_journals) == 0:
            suggestions.append("Create at least one sales journal")
        if int(purchase_journals) == 0:
            suggestions.append("Create at least one purchase journal")
        if int(bank_journals) == 0:
            suggestions.append("Create at least one bank/cash journal")

        return {
            "journals": int(journals),
            "accounts": int(accounts),
            "bank_journals": int(bank_journals),
            "sale_journals": int(sale_journals),
            "purchase_journals": int(purchase_journals),
            "ready": len(suggestions) == 0,
            "suggestions": suggestions,
        }

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
