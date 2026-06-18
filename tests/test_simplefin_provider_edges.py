"""Edge-case tests for SimpleFINHoldingsProvider (fixes applied in plan-3 wave)."""
from __future__ import annotations

import json

from plutus.providers.simplefin import SimpleFINHoldingsProvider


def _write_payload(tmp_path, accounts: list[dict]) -> str:
    p = tmp_path / "simplefin_edge.json"
    p.write_text(json.dumps({"accounts": accounts}))
    return str(p)


def _account(*, id="acc-1", name="Edge Brokerage", balance_date=None, holdings=None):
    a: dict = {"name": name, "currency": "USD", "balance": "1000.00"}
    if id is not None:
        a["id"] = id
    if balance_date is not None:
        a["balance-date"] = balance_date
    a["holdings"] = holdings or [
        {"symbol": "VTI", "description": "Vanguard Total", "shares": "5.0",
         "market_value": "500.00", "cost_basis": "450.00"}
    ]
    return a


# ---------------------------------------------------------------------------
# Fix #1 — as_of must never be None
# ---------------------------------------------------------------------------

def test_as_of_uses_explicit_fallback_when_no_balance_date(tmp_path):
    """With as_of_fallback set and no balance-date, holding.as_of == fallback."""
    path = _write_payload(tmp_path, [_account(balance_date=None)])
    p = SimpleFINHoldingsProvider(payload_path=path, as_of_fallback="2026-01-01")
    holdings = p.fetch_holdings()
    assert len(holdings) == 1
    assert holdings[0].as_of == "2026-01-01"


def test_as_of_defaults_to_today_when_no_fallback(tmp_path):
    """With no fallback and no balance-date, holding.as_of is a non-empty ISO date."""
    path = _write_payload(tmp_path, [_account(balance_date=None)])
    p = SimpleFINHoldingsProvider(payload_path=path)
    holdings = p.fetch_holdings()
    assert len(holdings) == 1
    assert holdings[0].as_of is not None
    assert len(holdings[0].as_of) == 10  # YYYY-MM-DD


def test_as_of_from_balance_date_takes_precedence_over_fallback(tmp_path):
    """When balance-date is present, it wins over as_of_fallback."""
    # epoch 1718582400 => 2024-06-17 UTC
    path = _write_payload(tmp_path, [_account(balance_date=1718582400)])
    p = SimpleFINHoldingsProvider(payload_path=path, as_of_fallback="2026-01-01")
    holdings = p.fetch_holdings()
    assert holdings[0].as_of == "2024-06-17"


# ---------------------------------------------------------------------------
# Fix #2 — cost_basis unparseable → None (not 0.0)
# ---------------------------------------------------------------------------

def test_cost_basis_garbage_string_becomes_none(tmp_path):
    """A non-numeric cost_basis string should parse to None, not 0.0."""
    account = _account(holdings=[
        {"symbol": "BAD", "description": "Bad Basis", "shares": "1.0",
         "market_value": "100.00", "cost_basis": "not-a-number"}
    ])
    path = _write_payload(tmp_path, [account])
    p = SimpleFINHoldingsProvider(payload_path=path)
    holdings = p.fetch_holdings()
    assert len(holdings) == 1
    assert holdings[0].cost_basis is None


def test_cost_basis_none_stays_none(tmp_path):
    """A missing cost_basis (null / omitted) should remain None."""
    account = _account(holdings=[
        {"symbol": "NO_CB", "description": "No Basis", "shares": "2.0",
         "market_value": "200.00"}
    ])
    path = _write_payload(tmp_path, [account])
    p = SimpleFINHoldingsProvider(payload_path=path)
    holdings = p.fetch_holdings()
    assert holdings[0].cost_basis is None


def test_cost_basis_valid_number_parsed(tmp_path):
    """A numeric cost_basis string is parsed correctly."""
    account = _account(holdings=[
        {"symbol": "OK", "description": "Ok", "shares": "3.0",
         "market_value": "300.00", "cost_basis": "270.00"}
    ])
    path = _write_payload(tmp_path, [account])
    p = SimpleFINHoldingsProvider(payload_path=path)
    holdings = p.fetch_holdings()
    assert holdings[0].cost_basis == 270.0


# ---------------------------------------------------------------------------
# Fix #3 — accounts missing id are excluded
# ---------------------------------------------------------------------------

def test_account_without_id_excluded_from_fetch_accounts(tmp_path):
    """An account dict with no 'id' key should be silently excluded."""
    good = _account(id="acc-good")
    bad = _account(id=None)  # id key omitted
    path = _write_payload(tmp_path, [good, bad])
    p = SimpleFINHoldingsProvider(payload_path=path)
    accounts = p.fetch_accounts()
    assert len(accounts) == 1
    assert accounts[0].id == "acc-good"


def test_account_without_id_excluded_from_fetch_holdings(tmp_path):
    """Holdings from an id-less account should not appear in fetch_holdings."""
    good = _account(id="acc-good", holdings=[
        {"symbol": "VTI", "shares": "1.0", "market_value": "100.00"}
    ])
    bad = _account(id=None, holdings=[
        {"symbol": "GHOST", "shares": "5.0", "market_value": "500.00"}
    ])
    path = _write_payload(tmp_path, [good, bad])
    p = SimpleFINHoldingsProvider(payload_path=path)
    symbols = {h.symbol for h in p.fetch_holdings()}
    assert "GHOST" not in symbols
    assert "VTI" in symbols
