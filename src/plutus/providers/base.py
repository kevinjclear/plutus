"""Provider contract — the swappable data-source interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from plutus.model import Account, Holding, Transaction


class Provider(ABC):
    """Read-only source of normalized financial data.

    Implementations MUST be read-only: no method may write to an institution.
    """

    name: str = "base"

    @abstractmethod
    def fetch_accounts(self) -> list[Account]:
        ...

    @abstractmethod
    def fetch_transactions(self) -> list[Transaction]:
        ...

    @abstractmethod
    def fetch_holdings(self) -> list[Holding]:
        ...
