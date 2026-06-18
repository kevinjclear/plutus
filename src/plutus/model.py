"""Core data model — the contract between providers, storage, and analysis."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Account:
    provider: str          # simplefin | actual | plaid
    institution: str       # Chase | AMEX | Ally | Wealthfront | Schwab | Vanguard
    name: str
    type: str              # checking|savings|brokerage|credit|loan|retirement
    tax_type: str          # taxable|traditional|roth|hsa|none
    currency: str = "USD"
    balance: float = 0.0
    is_liability: bool = False
    id: str | None = None          # provider-side account id
    last_updated: str | None = None  # ISO-8601


@dataclass
class Transaction:
    account_id: str
    date: str              # ISO YYYY-MM-DD
    amount: float          # signed; negative = outflow
    description: str
    provider_txn_id: str   # dedupe key
    category: str | None = None
    pending: bool = False


@dataclass
class Holding:
    account_id: str
    symbol: str
    quantity: float
    price: float
    market_value: float
    as_of: str             # ISO YYYY-MM-DD
    name: str | None = None
    cost_basis: float | None = None
    acquired_date: str | None = None
    bucket: str | None = None      # asset class; None until classified


@dataclass
class Snapshot:
    taken_at: str          # ISO-8601 timestamp
    net_worth: float
    total_assets: float
    total_liabilities: float
