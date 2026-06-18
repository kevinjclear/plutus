from plutus.model import Account, Transaction
from plutus.storage import Storage


def _seed_account(db):
    db.upsert_account(Account(provider="actual", institution="Chase", name="Checking",
                              type="checking", tax_type="none", id="chase-1"))


def test_add_transactions_dedupes(tmp_path):
    db = Storage(str(tmp_path / "f.db"))
    _seed_account(db)
    t1 = Transaction(account_id="chase-1", date="2026-06-01", amount=-10.0,
                     description="A", provider_txn_id="t1")
    t2 = Transaction(account_id="chase-1", date="2026-06-02", amount=-20.0,
                     description="B", provider_txn_id="t2")
    assert db.add_transactions([t1, t2]) == 2
    # re-adding t1 plus a new t3 inserts only t3
    t3 = Transaction(account_id="chase-1", date="2026-06-03", amount=-5.0,
                     description="C", provider_txn_id="t3")
    assert db.add_transactions([t1, t3]) == 1
    assert len(db.get_transactions("chase-1")) == 3
    db.close()
