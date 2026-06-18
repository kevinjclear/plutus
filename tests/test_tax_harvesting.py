from plutus.model import Holding, Transaction
from plutus.tax import investment_income, harvesting_candidates


def test_investment_income_sums_matching_categories():
    txns = [
        Transaction(account_id="b", date="2026-03-01", amount=120.0, description="Div",
                    provider_txn_id="d1", category="Dividends"),
        Transaction(account_id="b", date="2026-04-01", amount=15.0, description="Int",
                    provider_txn_id="i1", category="interest"),       # case-insensitive
        Transaction(account_id="b", date="2026-04-02", amount=-50.0, description="Fee",
                    provider_txn_id="f1", category="Fees"),
    ]
    assert investment_income(txns) == 135.0


def test_harvesting_only_taxable_losses():
    holds = [
        Holding(account_id="tax", symbol="GLD", quantity=20, price=200, market_value=4000.0,
                cost_basis=4600.0, as_of="2026-06-17"),     # loss -600, taxable -> candidate
        Holding(account_id="tax", symbol="QQQ", quantity=10, price=500, market_value=5000.0,
                cost_basis=4000.0, as_of="2026-06-17"),     # gain -> not a candidate
        Holding(account_id="ira", symbol="VTI", quantity=5, price=100, market_value=400.0,
                cost_basis=600.0, as_of="2026-06-17"),      # loss but NOT taxable -> excluded
        Holding(account_id="tax", symbol="XYZ", quantity=1, price=10, market_value=10.0,
                cost_basis=None, as_of="2026-06-17"),       # no basis -> excluded
    ]
    cands = harvesting_candidates(holds, taxable_account_ids={"tax"})
    assert [c["symbol"] for c in cands] == ["GLD"]
    assert cands[0]["unrealized_loss"] == -600.0
    assert cands[0]["wash_sale_caution"] is True
