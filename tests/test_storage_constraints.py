"""Constraint and invariant tests for Storage: FK enforcement, enum CHECKs,
snapshot atomicity, and deterministic transaction ordering."""
import sqlite3

import pytest

from plutus.model import Account, Holding, Snapshot, Transaction
from plutus.storage import Storage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_account(id="acc-1", type="checking", tax_type="none"):
    return Account(
        provider="simplefin", institution="Ally", name="Checking",
        type=type, tax_type=tax_type, id=id,
    )


def _valid_txn(provider_txn_id="t1", account_id="acc-1", date="2026-06-01"):
    return Transaction(
        account_id=account_id, date=date, amount=-10.0,
        description="Test", provider_txn_id=provider_txn_id,
    )


def _valid_holding(account_id="acc-1"):
    return Holding(
        account_id=account_id, symbol="VTI", quantity=1, price=100.0,
        market_value=100.0, as_of="2026-06-16",
    )


# ---------------------------------------------------------------------------
# 1. Enum CHECK constraints on accounts
# ---------------------------------------------------------------------------

class TestEnumConstraints:
    def test_invalid_account_type_raises(self, tmp_path):
        db = Storage(str(tmp_path / "f.db"))
        with pytest.raises(sqlite3.IntegrityError):
            db.upsert_account(_valid_account(type="crypto"))
        db.close()

    def test_invalid_tax_type_raises(self, tmp_path):
        db = Storage(str(tmp_path / "f.db"))
        with pytest.raises(sqlite3.IntegrityError):
            db.upsert_account(_valid_account(tax_type="Roth"))  # wrong case
        db.close()

    @pytest.mark.parametrize("t", ["checking", "savings", "brokerage", "credit", "loan", "retirement"])
    def test_all_valid_account_types_accepted(self, tmp_path, t):
        db = Storage(str(tmp_path / "f.db"))
        db.upsert_account(_valid_account(id=f"acc-{t}", type=t))
        db.close()

    @pytest.mark.parametrize("tt", ["taxable", "traditional", "roth", "hsa", "none"])
    def test_all_valid_tax_types_accepted(self, tmp_path, tt):
        db = Storage(str(tmp_path / "f.db"))
        db.upsert_account(_valid_account(id=f"acc-{tt}", tax_type=tt))
        db.close()


# ---------------------------------------------------------------------------
# 2. FK enforcement
# ---------------------------------------------------------------------------

class TestFKEnforcement:
    def test_foreign_keys_pragma_is_on(self, tmp_path):
        db = Storage(str(tmp_path / "f.db"))
        assert db.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        db.close()

    def test_add_transactions_unknown_account_raises(self, tmp_path):
        db = Storage(str(tmp_path / "f.db"))
        # No account seeded — FK should fire
        with pytest.raises(sqlite3.IntegrityError):
            db.add_transactions([_valid_txn(account_id="ghost-account")])
        db.close()

    def test_replace_holdings_unknown_account_raises(self, tmp_path):
        db = Storage(str(tmp_path / "f.db"))
        with pytest.raises(sqlite3.IntegrityError):
            db.replace_holdings("ghost-account", [_valid_holding(account_id="ghost-account")])
        db.close()


# ---------------------------------------------------------------------------
# 3. Snapshot atomicity
# ---------------------------------------------------------------------------

class TestSnapshotAtomicity:
    def _snapshot(self):
        return Snapshot(taken_at="2026-06-16T12:00:00", net_worth=500.0,
                        total_assets=600.0, total_liabilities=100.0)

    def test_empty_allocation_succeeds_and_returns_int(self, tmp_path):
        db = Storage(str(tmp_path / "f.db"))
        sid = db.write_snapshot(self._snapshot(), allocation={})
        assert isinstance(sid, int)
        db.close()

    def test_snapshot_and_allocation_rows_both_persisted(self, tmp_path):
        db = Storage(str(tmp_path / "f.db"))
        alloc = {"us_equity": 0.6, "bonds": 0.3, "cash": 0.1}
        sid = db.write_snapshot(self._snapshot(), allocation=alloc)

        # Snapshot row exists
        snaps = db.get_snapshots()
        assert len(snaps) == 1
        assert snaps[0].net_worth == 500.0

        # All allocation rows exist
        rows = db.conn.execute(
            "SELECT bucket, weight FROM snapshot_allocation WHERE snapshot_id=? ORDER BY bucket;",
            (sid,),
        ).fetchall()
        assert len(rows) == 3
        by_bucket = {r["bucket"]: r["weight"] for r in rows}
        assert by_bucket == alloc
        db.close()


# ---------------------------------------------------------------------------
# 4. Deterministic transaction ordering (same-date tie-breaking)
# ---------------------------------------------------------------------------

class TestTransactionOrdering:
    def test_same_date_ordered_by_provider_txn_id(self, tmp_path):
        db = Storage(str(tmp_path / "f.db"))
        db.upsert_account(_valid_account())
        # Insert in reverse provider_txn_id order so natural insert order would differ
        txns = [
            _valid_txn(provider_txn_id="tz", date="2026-06-01"),
            _valid_txn(provider_txn_id="ta", date="2026-06-01"),
            _valid_txn(provider_txn_id="tm", date="2026-06-01"),
        ]
        db.add_transactions(txns)
        got = db.get_transactions()
        ids = [t.provider_txn_id for t in got]
        assert ids == ["ta", "tm", "tz"], f"Expected stable order, got {ids}"
        db.close()

    def test_per_account_query_also_stable(self, tmp_path):
        db = Storage(str(tmp_path / "f.db"))
        db.upsert_account(_valid_account())
        txns = [
            _valid_txn(provider_txn_id="z9", date="2026-06-02"),
            _valid_txn(provider_txn_id="a1", date="2026-06-02"),
        ]
        db.add_transactions(txns)
        got = db.get_transactions("acc-1")
        ids = [t.provider_txn_id for t in got]
        assert ids == ["a1", "z9"], f"Expected stable per-account order, got {ids}"
        db.close()
