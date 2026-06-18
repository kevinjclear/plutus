"""SimpleFINHoldingsProvider — investment holdings from a SimpleFIN /accounts payload.

Read-only: parses a saved SimpleFIN JSON file (fetched by fetch_simplefin.py).
Emits only accounts that carry holdings (brokerage/retirement); banking/cash and
transactions come from Actual, so fetch_transactions() returns []."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import yaml

from plutus.model import Account, Holding, Transaction
from plutus.providers.base import Provider
from plutus.providers.accountmap import match_meta

logger = logging.getLogger(__name__)

_DEFAULTS = {"institution": "Unknown", "type": "brokerage",
             "tax_type": "taxable", "is_liability": False}


def _to_float(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _to_float_or_none(v) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _as_of(epoch) -> str | None:
    if not epoch:
        return None
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).date().isoformat()


class SimpleFINHoldingsProvider(Provider):
    name = "simplefin"

    def __init__(self, payload_path: str, accounts_config_path: str | None = None,
                 as_of_fallback: str | None = None):
        self._payload_path = payload_path
        self._accounts_config_path = accounts_config_path
        self._as_of_fallback = as_of_fallback
        self._payload: dict | None = None
        self._map: dict | None = None

    def _effective_as_of(self, epoch) -> str:
        result = _as_of(epoch)
        if result is not None:
            return result
        if self._as_of_fallback is not None:
            return self._as_of_fallback
        return datetime.now(timezone.utc).date().isoformat()

    def _load(self) -> dict:
        if self._payload is None:
            self._payload = json.loads(Path(self._payload_path).read_text())
        return self._payload

    def _load_map(self) -> dict:
        if self._map is None:
            cfg = {}
            if self._accounts_config_path:
                cfg = yaml.safe_load(Path(self._accounts_config_path).read_text()) or {}
            self._map = {"accounts": cfg.get("accounts") or {},
                         "defaults": {**_DEFAULTS, **(cfg.get("defaults") or {})}}
        return self._map

    def _investment_accounts(self) -> list[dict]:
        return [a for a in self._load().get("accounts", []) if a.get("id") and a.get("holdings")]

    def _meta_for(self, name: str) -> dict:
        m = self._load_map()
        entry = match_meta(name, m["accounts"])   # exact name, then account-number token
        if entry is None:
            logger.warning("SimpleFINHoldingsProvider: unmapped account %r — using defaults", name)
            return dict(m["defaults"])
        return {**m["defaults"], **entry}

    def unmapped_account_names(self) -> list[str]:
        m = self._load_map()
        seen, out = set(), []
        for a in self._investment_accounts():
            n = a.get("name")
            if match_meta(n, m["accounts"]) is None and n not in seen:
                seen.add(n)
                out.append(n)
        return out

    def fetch_accounts(self) -> list[Account]:
        out: list[Account] = []
        for a in self._investment_accounts():
            meta = self._meta_for(a.get("name"))
            out.append(Account(
                provider="simplefin", id=a["id"], institution=meta["institution"],
                name=a.get("name", a["id"]), type=meta["type"], tax_type=meta["tax_type"],
                currency=a.get("currency", "USD"), balance=_to_float(a.get("balance")),
                is_liability=bool(meta["is_liability"]), last_updated=_as_of(a.get("balance-date")),
            ))
        return out

    def fetch_holdings(self) -> list[Holding]:
        out: list[Holding] = []
        for a in self._investment_accounts():
            as_of = self._effective_as_of(a.get("balance-date"))
            for h in a.get("holdings", []):
                shares = _to_float(h.get("shares"))
                mv = _to_float(h.get("market_value"))
                out.append(Holding(
                    account_id=a["id"], symbol=h.get("symbol") or (h.get("description") or "?"),
                    name=h.get("description"), quantity=shares,
                    price=(mv / shares if shares else 0.0), market_value=mv,
                    cost_basis=_to_float_or_none(h.get("cost_basis")),
                    acquired_date=None, bucket=None, as_of=as_of,
                ))
        return out

    def fetch_transactions(self) -> list[Transaction]:
        return []
