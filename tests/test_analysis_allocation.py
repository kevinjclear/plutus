from plutus.model import Holding
from plutus.strategy import Strategy
from plutus.analysis import allocation, strategy_gap


def _holdings():
    return [
        Holding(account_id="s", symbol="QQQ", quantity=10, price=500, market_value=5000.0, as_of="2026-06-17"),
        Holding(account_id="s", symbol="GLD", quantity=20, price=200, market_value=4000.0, as_of="2026-06-17"),
        Holding(account_id="s", symbol="ZZZZ", quantity=1, price=1000, market_value=1000.0, as_of="2026-06-17"),
    ]


def _strategy():
    return Strategy(
        targets={"us_large_growth": 0.5, "gold": 0.0, "cash": 0.5},
        ticker_map={"QQQ": "us_large_growth", "GLD": "gold"},
    )


def test_allocation_buckets_and_weights_and_needs_classification():
    alloc = allocation(_holdings(), _strategy())          # total = 10000
    assert alloc["us_large_growth"]["value"] == 5000.0 and alloc["us_large_growth"]["weight"] == 0.5
    assert alloc["gold"]["weight"] == 0.4
    assert alloc["needs_classification"]["value"] == 1000.0 and alloc["needs_classification"]["weight"] == 0.1


def test_allocation_includes_cash():
    alloc = allocation(_holdings(), _strategy(), cash=10000.0)   # total = 20000
    assert alloc["cash"]["value"] == 10000.0 and alloc["cash"]["weight"] == 0.5
    assert alloc["us_large_growth"]["weight"] == 0.25


def test_strategy_gap_sorted_and_signed():
    gap = strategy_gap(_holdings(), _strategy())          # total 10000; no cash
    by = {g["bucket"]: g for g in gap}
    # gold over target: current 0.4 vs 0.0 -> +0.4
    assert round(by["gold"]["delta_weight"], 4) == 0.4
    assert round(by["gold"]["delta_value"], 2) == 4000.0
    # cash under target: current 0.0 vs 0.5 -> -0.5
    assert round(by["cash"]["delta_weight"], 4) == -0.5
    # us_large_growth: 0.5 vs 0.5 -> 0.0
    assert round(by["us_large_growth"]["delta_weight"], 4) == 0.0
    # sorted by |delta| desc: cash (0.5) first
    assert gap[0]["bucket"] == "cash"


def test_strategy_gap_unrounded_dollar_deltas():
    """delta_value must use raw (unrounded) weights × raw total.

    Old code rounded weights before multiplying, causing errors up to ~0.005×total
    per bucket (thousands of dollars on large portfolios). With uneven thirds the
    old path gives ~±170 000 instead of the correct ±166 667.
    """
    holdings = [
        Holding(account_id="a", symbol="QQQ", quantity=1, price=333333.0, market_value=333333.0, as_of="2026-06-17"),
        Holding(account_id="a", symbol="GLD", quantity=1, price=666667.0, market_value=666667.0, as_of="2026-06-17"),
    ]
    strategy = Strategy(
        targets={"us_large_growth": 0.5, "gold": 0.5},
        ticker_map={"QQQ": "us_large_growth", "GLD": "gold"},
    )
    gap = strategy_gap(holdings, strategy)
    by = {g["bucket"]: g for g in gap}
    assert abs(by["us_large_growth"]["delta_value"] - (-166667.0)) < 1.0, by["us_large_growth"]
    assert abs(by["gold"]["delta_value"] - 166667.0) < 1.0, by["gold"]


def test_allocation_respects_preset_bucket():
    from plutus.model import Holding
    s = Strategy(targets={"duration_bonds": 1.0}, ticker_map={})
    h = Holding(account_id="a", symbol="ZZZZ", quantity=1, price=0, market_value=1000.0,
                as_of="2026-06-18", bucket="duration_bonds")  # unknown symbol, bucket preset
    alloc = allocation([h], s)
    assert alloc["duration_bonds"]["weight"] == 1.0
    assert "needs_classification" not in alloc
