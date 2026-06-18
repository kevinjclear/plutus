import os

from plutus.model import Account, Holding
from plutus.providers.base import Provider
from plutus.providers.simplefin import SimpleFINHoldingsProvider

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
PAYLOAD = os.path.join(FIX, "simplefin_accounts.json")
CONFIG = os.path.join(FIX, "simplefin_accounts_map.yaml")


def _p():
    return SimpleFINHoldingsProvider(payload_path=PAYLOAD, accounts_config_path=CONFIG)


def test_is_provider():
    assert isinstance(_p(), Provider)
    assert _p().name == "simplefin"


def test_only_investment_accounts_returned():
    accts = {a.id: a for a in _p().fetch_accounts()}
    assert set(accts) == {"sf-schwab", "sf-wf"}      # chase has no holdings -> excluded
    assert accts["sf-schwab"].institution == "Schwab"
    assert accts["sf-schwab"].type == "brokerage" and accts["sf-schwab"].tax_type == "taxable"
    assert accts["sf-schwab"].balance == 52000.0
    assert accts["sf-schwab"].provider == "simplefin"


def test_unmapped_uses_defaults_and_is_surfaced():
    p = _p()
    wf = {a.id: a for a in p.fetch_accounts()}["sf-wf"]
    assert wf.institution == "Unknown" and wf.type == "brokerage" and wf.tax_type == "taxable"
    assert p.unmapped_account_names() == ["Wealthfront Individual"]


def test_holdings_parsed_with_prices_and_basis():
    holds = {h.symbol: h for h in _p().fetch_holdings()}
    assert set(holds) == {"QQQ", "GLD", "VTI"}
    qqq = holds["QQQ"]
    assert qqq.account_id == "sf-schwab" and qqq.quantity == 10.0
    assert qqq.market_value == 5000.0 and qqq.cost_basis == 4000.0
    assert qqq.price == 500.0                         # 5000 / 10
    assert qqq.name == "Invesco QQQ Trust" and qqq.bucket is None
    assert qqq.as_of == "2024-06-17"                  # from balance-date epoch
    assert holds["GLD"].cost_basis == 4600.0


def test_transactions_empty():
    assert _p().fetch_transactions() == []
