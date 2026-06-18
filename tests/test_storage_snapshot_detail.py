from plutus.model import Account, Holding, Snapshot
from plutus.storage import Storage


def test_add_snapshot_detail_persists(tmp_path):
    db = Storage(str(tmp_path / "f.db"))
    db.upsert_account(Account(provider="simplefin", id="s", institution="Schwab", name="B",
                              type="brokerage", tax_type="taxable"))
    sid = db.write_snapshot(Snapshot(taken_at="2026-06-17T08:00:00", net_worth=5000.0,
                                     total_assets=5000.0, total_liabilities=0.0),
                            allocation={"us_large_growth": 1.0})
    accts = [Account(provider="simplefin", id="s", institution="Schwab", name="B",
                     type="brokerage", tax_type="taxable", balance=5000.0)]
    holds = [Holding(account_id="s", symbol="QQQ", quantity=10, price=500,
                     market_value=5000.0, as_of="2026-06-17")]
    db.add_snapshot_detail(sid, accts, holds)
    bal = db.conn.execute("SELECT balance FROM snapshot_balances WHERE snapshot_id=? AND account_id='s'",
                          (sid,)).fetchone()
    assert bal["balance"] == 5000.0
    h = db.conn.execute("SELECT market_value FROM snapshot_holdings WHERE snapshot_id=? AND symbol='QQQ'",
                        (sid,)).fetchone()
    assert h["market_value"] == 5000.0
    db.close()
