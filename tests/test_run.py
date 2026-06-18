import os

from plutus.model import Account, Holding, Transaction
from plutus.providers.fake import FakeProvider
from plutus.strategy import Strategy
from plutus.storage import Storage
from plutus.run import assemble_dataset, build_report_data, run_once


def _actual():
    return FakeProvider(
        accounts=[
            Account(provider="actual", id="chk", institution="Chase", name="Checking",
                    type="checking", tax_type="none", balance=2500.0),
            Account(provider="actual", id="amex", institution="AMEX", name="Card",
                    type="credit", tax_type="none", balance=-1200.0, is_liability=True),
            Account(provider="actual", id="a-sch", institution="Schwab", name="Brokerage",
                    type="brokerage", tax_type="taxable", balance=99999.0),  # must be dropped
        ],
        transactions=[
            Transaction(account_id="chk", date="2026-06-30", amount=3000.0, description="Pay",
                        provider_txn_id="t1", category="Income"),
            # belongs to the dropped brokerage account -> must be filtered out (FK safety)
            Transaction(account_id="a-sch", date="2026-06-15", amount=-50.0, description="Fee",
                        provider_txn_id="t-drop", category="Fees"),
        ],
    )


def _simplefin():
    return FakeProvider(
        accounts=[
            Account(provider="simplefin", id="s-sch", institution="Schwab", name="Brokerage",
                    type="brokerage", tax_type="taxable", balance=9000.0),
        ],
        holdings=[
            Holding(account_id="s-sch", symbol="QQQ", quantity=10, price=500, market_value=5000.0,
                    cost_basis=4000.0, as_of="2026-06-17"),
            Holding(account_id="s-sch", symbol="GLD", quantity=20, price=200, market_value=4000.0,
                    cost_basis=4600.0, as_of="2026-06-17"),
        ],
    )


def _strategy():
    return Strategy(targets={"us_large_growth": 0.5, "gold": 0.0, "cash": 0.5},
                    ticker_map={"QQQ": "us_large_growth", "GLD": "gold"})


def test_assemble_drops_actual_investment_accounts():
    accts, txns, holds = assemble_dataset([_actual(), _simplefin()])
    ids = {a.id for a in accts}
    assert "a-sch" not in ids                     # Actual brokerage dropped
    assert {"chk", "amex", "s-sch"} <= ids        # cash/credit + SimpleFIN brokerage kept
    assert len(holds) == 2
    # the dropped brokerage's transaction is filtered out (FK safety); only "chk"'s remains
    txn_ids = {t.provider_txn_id for t in txns}
    assert txn_ids == {"t1"} and "t-drop" not in txn_ids


def test_build_report_data_values():
    accts, txns, holds = assemble_dataset([_actual(), _simplefin()])
    data = build_report_data(accts, txns, holds, _strategy(),
                             generated_at="2026-06-17T08:00:00",
                             unmapped=["Wealthfront Individual"])
    # net worth = 2500 - 1200 + 9000 = 10300
    assert data["net_worth"]["net_worth"] == 10300.0
    # harvesting: GLD loss only (taxable)
    assert [h["symbol"] for h in data["harvesting"]] == ["GLD"]
    assert any("Wealthfront" in s for s in data["needs_attention"])


def test_run_once_writes_report(tmp_path):
    db = Storage(str(tmp_path / "f.db"))
    out = run_once([_actual(), _simplefin()], db, _strategy(), str(tmp_path),
                   generated_at="2026-06-17T08:00:00")
    assert os.path.exists(out)
    md = open(out).read()
    assert "Net worth" in md and "$10,300" in md
    # snapshot persisted
    assert len(db.get_snapshots()) == 1
    db.close()


def test_expand_lookthrough_splits_fund():
    from plutus.model import Holding
    from plutus.run import expand_lookthrough
    s = Strategy(targets={}, ticker_map={},
                 lookthrough=[{"match_description": "Target Retire 2060",
                               "split": {"us_large_growth": 0.5, "duration_bonds": 0.5}}])
    h = Holding(account_id="v", symbol=None, name="Target Retire 2060 Tr",
                quantity=1, price=0, market_value=200000.0, as_of="2026-06-18")
    out = expand_lookthrough([h], s)
    assert len(out) == 2
    by = {x.bucket: x.market_value for x in out}
    assert by["us_large_growth"] == 100000.0 and by["duration_bonds"] == 100000.0
    q = Holding(account_id="v", symbol="QQQ", name="QQQ", quantity=1, price=0,
                market_value=10.0, as_of="2026-06-18")
    assert expand_lookthrough([q], s) == [q]
