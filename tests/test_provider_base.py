import pytest

from plutus.model import Account, Holding, Transaction
from plutus.providers.base import Provider
from plutus.providers.fake import FakeProvider


def test_cannot_instantiate_abstract_provider():
    with pytest.raises(TypeError):
        Provider()  # abstract


def test_fake_provider_returns_seeded_data():
    acc = Account(provider="fake", institution="Test", name="Acc",
                  type="brokerage", tax_type="taxable", id="a1")
    txn = Transaction(account_id="a1", date="2026-06-01", amount=-1.0,
                      description="x", provider_txn_id="t1")
    hold = Holding(account_id="a1", symbol="QQQ", quantity=1, price=1.0,
                   market_value=1.0, as_of="2026-06-16")
    p = FakeProvider(accounts=[acc], transactions=[txn], holdings=[hold])
    assert isinstance(p, Provider)
    assert p.name == "fake"
    assert p.fetch_accounts()[0].id == "a1"
    assert p.fetch_transactions()[0].provider_txn_id == "t1"
    assert p.fetch_holdings()[0].symbol == "QQQ"


def test_fake_provider_defaults_empty():
    p = FakeProvider()
    assert p.fetch_accounts() == []
    assert p.fetch_transactions() == []
    assert p.fetch_holdings() == []
