from plutus.model import Account, Holding
from plutus.storage import Storage


def _seed(db):
    db.upsert_account(Account(provider="simplefin", institution="Schwab", name="Brokerage",
                              type="brokerage", tax_type="taxable", id="schwab-1"))


def test_replace_holdings_is_idempotent(tmp_path):
    db = Storage(str(tmp_path / "f.db"))
    _seed(db)
    h = Holding(account_id="schwab-1", symbol="QQQ", quantity=10, price=500.0,
                market_value=5000.0, as_of="2026-06-16")
    assert db.replace_holdings("schwab-1", [h]) == 1
    # a later fetch replaces rather than appends
    h2 = Holding(account_id="schwab-1", symbol="QQQ", quantity=12, price=510.0,
                 market_value=6120.0, as_of="2026-06-17")
    db.replace_holdings("schwab-1", [h2])
    got = db.get_holdings("schwab-1")
    assert len(got) == 1 and got[0].quantity == 12 and got[0].market_value == 6120.0
    db.close()
