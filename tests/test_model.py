from plutus.model import Account, Transaction, Holding, Snapshot


def test_account_defaults():
    a = Account(provider="simplefin", institution="Ally", name="Savings",
                type="savings", tax_type="none")
    assert a.currency == "USD"
    assert a.balance == 0.0
    assert a.is_liability is False
    assert a.id is None


def test_liability_account_flag():
    amex = Account(provider="actual", institution="AMEX", name="Card",
                   type="credit", tax_type="none", balance=-1200.0, is_liability=True)
    assert amex.is_liability is True
    assert amex.balance == -1200.0


def test_transaction_and_holding_and_snapshot():
    t = Transaction(account_id="acc1", date="2026-06-01", amount=-42.5,
                    description="Coffee", provider_txn_id="txn-1")
    assert t.pending is False and t.category is None

    h = Holding(account_id="acc2", symbol="QQQ", quantity=10, price=500.0,
                market_value=5000.0, as_of="2026-06-16")
    assert h.bucket is None and h.cost_basis is None

    s = Snapshot(taken_at="2026-06-16T08:00:00", net_worth=123.0,
                 total_assets=200.0, total_liabilities=77.0)
    assert s.net_worth == 123.0
