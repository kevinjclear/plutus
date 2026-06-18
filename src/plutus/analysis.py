"""Pure analytics over model objects: net worth, cash flow, allocation, strategy gap."""
from __future__ import annotations

from collections import defaultdict

from plutus.model import Account, Holding, Transaction
from plutus.strategy import Strategy


def _round2(x: float) -> float:
    return round(x + 0.0, 2)


def net_worth(accounts: list[Account]) -> dict:
    total_assets = sum(a.balance for a in accounts if not a.is_liability)
    total_liabilities = sum(abs(a.balance) for a in accounts if a.is_liability)
    return {
        "total_assets": _round2(total_assets),
        "total_liabilities": _round2(total_liabilities),
        "net_worth": _round2(total_assets - total_liabilities),
    }


def cash_flow_by_category(transactions: list[Transaction], month: str | None = None) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for t in transactions:
        if month and not t.date.startswith(month):
            continue
        out[t.category or "uncategorized"] += t.amount
    return {k: _round2(v) for k, v in out.items()}


def monthly_cash_flow(transactions: list[Transaction]) -> dict[str, dict]:
    out: dict[str, dict] = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "net": 0.0})
    for t in transactions:
        ym = t.date[:7]
        bucket = out[ym]
        if t.amount >= 0:
            bucket["income"] += t.amount
        else:
            bucket["expense"] += t.amount
        bucket["net"] += t.amount
    return {ym: {k: _round2(v) for k, v in d.items()} for ym, d in out.items()}


def _raw_allocation(holdings: list[Holding], strategy: Strategy, cash: float = 0.0):
    """Returns (raw bucket->market_value dict, raw total) — UNROUNDED."""
    values: dict[str, float] = defaultdict(float)
    for h in holdings:
        # A pre-set bucket (e.g. from fund look-through or manual classification)
        # wins over symbol lookup.
        bucket = h.bucket or strategy.bucket_for(h.symbol)
        values[bucket] += h.market_value
    if cash:
        values["cash"] += cash
    return values, sum(values.values())


def allocation(holdings: list[Holding], strategy: Strategy, cash: float = 0.0) -> dict[str, dict]:
    values, total = _raw_allocation(holdings, strategy, cash)
    return {
        b: {"value": _round2(v), "weight": (_round2(v / total) if total else 0.0)}
        for b, v in values.items()
    }


def strategy_gap(holdings: list[Holding], strategy: Strategy, cash: float = 0.0) -> list[dict]:
    values, total = _raw_allocation(holdings, strategy, cash)
    buckets = set(strategy.targets) | set(values)
    rows = []
    for b in buckets:
        current_w = (values.get(b, 0.0) / total) if total else 0.0     # UNROUNDED
        target_w = strategy.targets.get(b, 0.0)
        delta_w = current_w - target_w                                  # UNROUNDED
        rows.append({
            "bucket": b,
            "current_weight": _round2(current_w),
            "target_weight": _round2(target_w),
            "delta_weight": _round2(delta_w),
            "current_value": _round2(values.get(b, 0.0)),
            "delta_value": _round2(delta_w * total),                    # raw delta_w * raw total
        })
    rows.sort(key=lambda r: abs(r["delta_weight"]), reverse=True)
    return rows
