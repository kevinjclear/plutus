from plutus.model import Account, Transaction
from plutus.analysis import net_worth, cash_flow_by_category, monthly_cash_flow


def _accts():
    return [
        Account(provider="actual", id="chk", institution="Chase", name="Checking",
                type="checking", tax_type="none", balance=2500.0, is_liability=False),
        Account(provider="actual", id="amex", institution="AMEX", name="Card",
                type="credit", tax_type="none", balance=-1200.0, is_liability=True),
        Account(provider="simplefin", id="sch", institution="Schwab", name="Brokerage",
                type="brokerage", tax_type="taxable", balance=50000.0, is_liability=False),
    ]


def test_net_worth_nets_liabilities():
    nw = net_worth(_accts())
    assert nw["total_assets"] == 52500.0
    assert nw["total_liabilities"] == 1200.0
    assert nw["net_worth"] == 51300.0


def test_liability_sign_robust_to_positive_balance():
    a = [Account(provider="x", id="c", institution="i", name="n", type="credit",
                 tax_type="none", balance=1000.0, is_liability=True)]   # stored positive
    assert net_worth(a)["net_worth"] == -1000.0


def _txns():
    return [
        Transaction(account_id="chk", date="2026-06-01", amount=-42.5, description="Coffee",
                    provider_txn_id="t1", category="Dining"),
        Transaction(account_id="chk", date="2026-06-15", amount=-100.0, description="Gas",
                    provider_txn_id="t2", category="Auto"),
        Transaction(account_id="chk", date="2026-06-30", amount=3000.0, description="Pay",
                    provider_txn_id="t3", category="Income"),
        Transaction(account_id="chk", date="2026-05-20", amount=-20.0, description="Snack",
                    provider_txn_id="t4", category=None),
    ]


def test_cash_flow_by_category_with_month_filter():
    cf = cash_flow_by_category(_txns(), month="2026-06")
    assert cf["Dining"] == -42.5 and cf["Auto"] == -100.0 and cf["Income"] == 3000.0
    assert "uncategorized" not in cf            # the uncategorized txn is in May
    assert cash_flow_by_category(_txns())["uncategorized"] == -20.0


def test_monthly_cash_flow():
    m = monthly_cash_flow(_txns())
    assert m["2026-06"]["income"] == 3000.0
    assert m["2026-06"]["expense"] == -142.5
    assert m["2026-06"]["net"] == 2857.5
    assert m["2026-05"]["expense"] == -20.0
