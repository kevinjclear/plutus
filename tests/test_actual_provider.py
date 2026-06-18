import os

from plutus.model import Account, Transaction
from plutus.providers.actual import ActualProvider
from plutus.providers.base import Provider

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
EXPORT = os.path.join(FIX, "actual_export.json")
CONFIG = os.path.join(FIX, "actual_accounts.yaml")


def _provider():
    return ActualProvider(export_path=EXPORT, accounts_config_path=CONFIG)


def test_is_a_provider():
    assert isinstance(_provider(), Provider)
    assert _provider().name == "actual"


def test_fetch_accounts_maps_metadata_and_converts_cents():
    accts = {a.id: a for a in _provider().fetch_accounts()}
    chase = accts["acc-chase"]
    assert chase.institution == "Chase" and chase.type == "checking"
    assert chase.tax_type == "none" and chase.is_liability is False
    assert chase.balance == 2500.0          # 250000 cents -> dollars
    assert chase.provider == "actual" and chase.currency == "USD"
    amex = accts["acc-amex"]
    assert amex.is_liability is True and amex.balance == -1200.0


def test_unmapped_account_falls_back_to_defaults():
    accts = {a.id: a for a in _provider().fetch_accounts()}
    schwab = accts["acc-schwab"]                 # not in the config
    assert schwab.institution == "Unknown" and schwab.type == "checking"
    assert schwab.balance == 50000.0


def test_fetch_transactions_amounts_description_and_pending():
    txns = {t.provider_txn_id: t for t in _provider().fetch_transactions()}
    t1 = txns["t1"]
    assert t1.account_id == "acc-chase" and t1.amount == -42.5
    assert t1.description == "Coffee Shop" and t1.category == "Dining"
    assert t1.pending is False                   # cleared -> not pending
    t2 = txns["t2"]
    assert t2.amount == 1500.0
    assert t2.description == "June paycheck"     # payee null -> falls back to notes
    assert t2.pending is True                    # not cleared -> pending


def test_fetch_holdings_is_empty():
    assert _provider().fetch_holdings() == []


def test_no_config_uses_defaults():
    p = ActualProvider(export_path=EXPORT)       # no config path
    chase = {a.id: a for a in p.fetch_accounts()}["acc-chase"]
    assert chase.institution == "Unknown" and chase.balance == 2500.0


def test_fetch_accounts_excludes_closed():
    accts = {a.id: a for a in _provider().fetch_accounts()}
    assert "acc-old" not in accts, "closed account acc-old must be excluded from fetch_accounts"


def test_fetch_transactions_excludes_closed_account_transactions():
    txns = {t.provider_txn_id: t for t in _provider().fetch_transactions()}
    assert "t3" not in txns, "transaction t3 on closed account must be excluded from fetch_transactions"


def test_unmapped_account_names_returns_non_closed_unmapped():
    # Chase Checking and AMEX are in the config; Old Savings is closed (excluded);
    # Schwab Brokerage is non-closed and NOT in the config -> should appear.
    unmapped = _provider().unmapped_account_names()
    assert unmapped == ["Schwab Brokerage"]
