"""ActualProvider — banking data from an Actual Budget export (read-only).

Reads the JSON produced by the Node exporter (exporter/index.js) plus an
account-mapping config, and maps to the core model. Actual tracks no
investment holdings, so fetch_holdings() returns []."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

from plutus.model import Account, Holding, Transaction
from plutus.providers.base import Provider
from plutus.providers.accountmap import match_meta

logger = logging.getLogger(__name__)

_DEFAULTS = {"institution": "Unknown", "type": "checking",
             "tax_type": "none", "is_liability": False}


class ActualProvider(Provider):
    name = "actual"

    def __init__(self, export_path: str, accounts_config_path: str | None = None):
        self._export_path = export_path
        self._accounts_config_path = accounts_config_path
        self._export: dict | None = None
        self._account_map: dict | None = None

    def _load_export(self) -> dict:
        if self._export is None:
            self._export = json.loads(Path(self._export_path).read_text())
        return self._export

    def _load_account_map(self) -> dict:
        if self._account_map is None:
            cfg = {}
            if self._accounts_config_path:
                cfg = yaml.safe_load(Path(self._accounts_config_path).read_text()) or {}
            self._account_map = {
                "accounts": cfg.get("accounts") or {},
                "defaults": {**_DEFAULTS, **(cfg.get("defaults") or {})},
            }
        return self._account_map

    def _meta_for(self, name: str) -> dict:
        m = self._load_account_map()
        entry = match_meta(name, m["accounts"])   # exact name, then account-number token
        if entry is None:
            logger.warning("ActualProvider: account %r not matched in config "
                           "(by name or account number); using defaults", name)
            return dict(m["defaults"])
        return {**m["defaults"], **entry}

    def unmapped_account_names(self) -> list[str]:
        """Return names of non-closed export accounts that match no config entry
        (by name or account-number token). Export order, de-duplicated.
        """
        export = self._load_export()
        m = self._load_account_map()
        seen: set[str] = set()
        out: list[str] = []
        for a in export.get("accounts", []):
            if a.get("closed"):
                continue
            name = a["name"]
            if match_meta(name, m["accounts"]) is None and name not in seen:
                seen.add(name)
                out.append(name)
        return out

    def fetch_accounts(self) -> list[Account]:
        export = self._load_export()
        out: list[Account] = []
        for a in export.get("accounts", []):
            if a.get("closed"):
                continue
            meta = self._meta_for(a["name"])
            out.append(Account(
                provider="actual", id=a["id"], institution=meta["institution"],
                name=a["name"], type=meta["type"], tax_type=meta["tax_type"],
                currency="USD", balance=(a.get("balance") or 0) / 100.0,
                is_liability=bool(meta["is_liability"]),
                last_updated=export.get("exported_at"),
            ))
        return out

    def fetch_transactions(self) -> list[Transaction]:
        export = self._load_export()
        non_closed_ids: set[str] = {
            a["id"] for a in export.get("accounts", []) if not a.get("closed")
        }
        out: list[Transaction] = []
        for t in export.get("transactions", []):
            if t["account"] not in non_closed_ids:
                continue
            desc = t.get("payee_name") or t.get("notes") or "(no description)"
            out.append(Transaction(
                account_id=t["account"], date=t["date"],
                amount=(t.get("amount") or 0) / 100.0, description=desc,
                provider_txn_id=t["id"], category=t.get("category_name"),
                pending=not bool(t.get("cleared", False)),
            ))
        return out

    def fetch_holdings(self) -> list[Holding]:
        return []
