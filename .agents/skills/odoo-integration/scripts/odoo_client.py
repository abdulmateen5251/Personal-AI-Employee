from __future__ import annotations

import os
import xmlrpc.client
from dataclasses import dataclass


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

    def list_partners(self, limit: int = 10):
        return self.models.execute_kw(
            self.config.db,
            self.uid,
            self.config.password,
            "res.partner",
            "search_read",
            [[]],
            {"fields": ["name", "email"], "limit": limit},
        )


def from_env() -> OdooClient:
    cfg = OdooConfig(
        url=os.getenv("ODOO_URL", "http://localhost:8069"),
        db=os.getenv("ODOO_DB", "odoo_db"),
        user=os.getenv("ODOO_USER", "admin"),
        password=os.getenv("ODOO_PASSWORD", "admin"),
    )
    return OdooClient(cfg)
