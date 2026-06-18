"""In-memory provider for deterministic tests (no network, no secrets)."""
from __future__ import annotations

from plutus.model import Account, Holding, Transaction
from plutus.providers.base import Provider


class FakeProvider(Provider):
    name = "fake"

    def __init__(self, accounts: list[Account] | None = None,
                 transactions: list[Transaction] | None = None,
                 holdings: list[Holding] | None = None):
        self._accounts = accounts or []
        self._transactions = transactions or []
        self._holdings = holdings or []

    def fetch_accounts(self) -> list[Account]:
        return list(self._accounts)

    def fetch_transactions(self) -> list[Transaction]:
        return list(self._transactions)

    def fetch_holdings(self) -> list[Holding]:
        return list(self._holdings)
