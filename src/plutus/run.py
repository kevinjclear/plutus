"""Orchestration: assemble provider data (reconciled), store, analyze, snapshot, render."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from plutus.model import Snapshot
from plutus.providers.base import Provider
from plutus.storage import Storage
from plutus.strategy import Strategy
from plutus import analysis
from plutus import tax

_INVESTMENT_TYPES = {"brokerage", "retirement"}


def expand_lookthrough(holdings, strategy: Strategy):
    """Split fund holdings across buckets per strategy look-through rules.

    A matched holding (e.g. a target-date fund with no ticker) becomes one
    synthetic holding per component bucket, with market_value pro-rated and the
    bucket pre-set. Used for allocation/strategy-gap only — not for storage or
    harvesting, which keep the real positions."""
    out = []
    for h in holdings:
        rule = strategy.lookthrough_for(h)
        if not rule:
            out.append(h)
            continue
        for bucket, weight in (rule.get("split") or {}).items():
            out.append(replace(h, market_value=round(h.market_value * float(weight), 2),
                               bucket=bucket))
    return out


def assemble_dataset(providers: list[Provider]):
    accounts, transactions, holdings = [], [], []
    for p in providers:
        accs = p.fetch_accounts()
        # Drop Actual-provider investment accounts (SimpleFIN owns those balances/holdings).
        accs = [a for a in accs if not (a.provider == "actual" and a.type in _INVESTMENT_TYPES)]
        accounts.extend(accs)
        # Transaction ownership: only Actual provides transactions today (SimpleFINHoldingsProvider
        # returns []). If a future provider returns transactions, reconcile here to avoid double-counting.
        transactions.extend(p.fetch_transactions())
        holdings.extend(p.fetch_holdings())
    # Keep only transactions whose account survived reconciliation — a dropped account's
    # transactions would otherwise violate the holdings/accounts FK at storage time.
    kept = {a.id for a in accounts}
    transactions = [t for t in transactions if t.account_id in kept]
    return accounts, transactions, holdings


def build_report_data(accounts, transactions, holdings, strategy: Strategy, *,
                      generated_at: str, withholding: dict | None = None, unmapped=()):
    cash = sum(a.balance for a in accounts if a.type in ("checking", "savings"))
    # Look-through funds for allocation/gap; harvesting + storage use the real positions.
    classified = expand_lookthrough(holdings, strategy)
    alloc = analysis.allocation(classified, strategy, cash=cash)
    taxable_ids = {a.id for a in accounts if a.tax_type == "taxable"}
    needs_attention = [f"Unmapped account: {n!r}" for n in unmapped]
    if alloc.get("needs_classification", {}).get("weight", 0) > 0:
        needs_attention.append(
            f"Unclassified holdings = {alloc['needs_classification']['weight'] * 100:.1f}% "
            "of the portfolio — add them to strategy.yaml tickers.")
    return {
        "generated_at": generated_at,
        "net_worth": analysis.net_worth(accounts),
        "monthly_cash_flow": analysis.monthly_cash_flow(transactions),
        "allocation": alloc,
        "strategy_gap": analysis.strategy_gap(classified, strategy, cash=cash),
        "harvesting": tax.harvesting_candidates(holdings, taxable_ids),
        "needs_attention": needs_attention,
        "withholding": withholding,
    }


def run_once(providers, storage: Storage, strategy: Strategy, out_dir: str, *,
             generated_at: str, withholding: dict | None = None, unmapped=()) -> str:
    from plutus.report import render_report

    accounts, transactions, holdings = assemble_dataset(providers)

    for a in accounts:
        storage.upsert_account(a)
    if transactions:
        storage.add_transactions(transactions)
    by_account: dict[str, list] = {}
    for h in holdings:
        by_account.setdefault(h.account_id, []).append(h)
    for account_id, hs in by_account.items():
        storage.replace_holdings(account_id, hs)

    data = build_report_data(accounts, transactions, holdings, strategy,
                             generated_at=generated_at, withholding=withholding, unmapped=unmapped)
    nw = data["net_worth"]
    sid = storage.write_snapshot(
        Snapshot(taken_at=generated_at, net_worth=nw["net_worth"],
                 total_assets=nw["total_assets"], total_liabilities=nw["total_liabilities"]),
        allocation={b: a["weight"] for b, a in data["allocation"].items()})
    storage.add_snapshot_detail(sid, accounts, holdings)

    md = render_report(data)
    out = Path(out_dir) / f"report-{generated_at[:10]}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md)
    return str(out)
