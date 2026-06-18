from plutus.model import Account
from plutus.storage import Storage


def test_upsert_and_get_account(tmp_path):
    db = Storage(str(tmp_path / "f.db"))
    acc = Account(provider="simplefin", institution="Ally", name="Savings",
                  type="savings", tax_type="none", balance=100.0, id="ally-1")
    acc_id = db.upsert_account(acc)
    assert acc_id == "ally-1"
    got = db.get_accounts()
    assert len(got) == 1
    assert got[0].institution == "Ally" and got[0].balance == 100.0
    db.close()


def test_upsert_updates_existing(tmp_path):
    db = Storage(str(tmp_path / "f.db"))
    base = dict(provider="simplefin", institution="Ally", name="Savings",
                type="savings", tax_type="none", id="ally-1")
    db.upsert_account(Account(balance=100.0, **base))
    db.upsert_account(Account(balance=250.0, **base))
    got = db.get_accounts()
    assert len(got) == 1            # updated, not duplicated
    assert got[0].balance == 250.0
    db.close()
