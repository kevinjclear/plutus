import os

from plutus.strategy import Strategy, load_strategy

FIX = os.path.join(os.path.dirname(__file__), "..", "strategy.yaml")


def test_bucket_for_known_and_unknown():
    s = Strategy(targets={"gold": 0.0}, ticker_map={"GLD": "gold"})
    assert s.bucket_for("GLD") == "gold"
    assert s.bucket_for("gld") == "gold"          # case-insensitive
    assert s.bucket_for("ZZZZ") == "needs_classification"


def test_load_strategy_reads_targets_and_tickers():
    s = load_strategy(os.path.abspath(FIX))
    assert abs(sum(s.targets.values()) - 1.0) < 1e-9   # longs sum to 1.0
    assert s.bucket_for("QQQ") == "us_large_growth"
    assert s.bucket_for("GLD") == "gold"
    assert s.targets["gold"] == 0.0


def test_lookthrough_for_matches_description():
    from plutus.model import Holding
    s = Strategy(targets={}, ticker_map={},
                 lookthrough=[{"match_description": "Target Retire 2060",
                               "split": {"us_large_growth": 0.6, "duration_bonds": 0.4}}])
    h = Holding(account_id="a", symbol=None, name="Target Retire 2060 Tr",
                quantity=1, price=0, market_value=1000.0, as_of="2026-06-18")
    rule = s.lookthrough_for(h)
    assert rule and rule["split"]["us_large_growth"] == 0.6
    h2 = Holding(account_id="a", symbol="QQQ", name="Invesco QQQ",
                 quantity=1, price=0, market_value=1.0, as_of="2026-06-18")
    assert s.lookthrough_for(h2) is None
