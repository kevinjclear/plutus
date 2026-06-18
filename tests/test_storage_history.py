from plutus.model import Snapshot
from plutus.storage import Storage


def test_write_and_get_snapshot(tmp_path):
    db = Storage(str(tmp_path / "f.db"))
    s = Snapshot(taken_at="2026-06-16T08:00:00", net_worth=300.0,
                 total_assets=400.0, total_liabilities=100.0)
    sid = db.write_snapshot(s, allocation={"us_large_growth": 0.6, "cash": 0.4})
    assert isinstance(sid, int)
    snaps = db.get_snapshots()
    assert len(snaps) == 1 and snaps[0].net_worth == 300.0
    db.close()


def test_fetch_run_lifecycle(tmp_path):
    db = Storage(str(tmp_path / "f.db"))
    rid = db.start_fetch_run("simplefin", "2026-06-16T08:00:00")
    db.finish_fetch_run(rid, "ok")
    row = db.conn.execute("SELECT status FROM fetch_runs WHERE run_id=?;", (rid,)).fetchone()
    assert row["status"] == "ok"
    db.close()
