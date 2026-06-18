"""Tax analytics — EDUCATIONAL ESTIMATES ONLY, not tax advice. Consult a CPA.

Personal numbers come from a TaxProfile (tax_profile.yaml), never hardcoded.
Investment income is treated as ordinary for the projection; LTCG preferential
rates and NIIT are out of scope. Realized gains are not computed (no lot data);
harvesting works on unrealized losses."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from plutus.model import Holding, Transaction


@dataclass
class TaxProfile:
    filing_status: str
    federal_brackets: list[dict]
    standard_deduction: float
    state_rate: float


def load_tax_profile(path: str) -> TaxProfile:
    cfg = yaml.safe_load(Path(path).read_text()) or {}
    return TaxProfile(
        filing_status=cfg.get("filing_status", "single"),
        federal_brackets=cfg.get("federal_brackets") or [],
        standard_deduction=float(cfg.get("standard_deduction", 0.0)),
        state_rate=float(cfg.get("state_rate", 0.0)),
    )


def estimate_federal_tax(taxable_income: float, brackets: list[dict]) -> float:
    tax = 0.0
    lower = 0.0
    for b in brackets:
        if taxable_income <= lower:
            break
        cap = b.get("up_to")
        upper = float("inf") if cap is None else float(cap)
        taxed = min(taxable_income, upper) - lower
        tax += taxed * float(b["rate"])
        lower = upper
    return round(tax, 2)


def withholding_gap(*, wages: float, withheld_ytd: float, profile: TaxProfile,
                    investment_income: float = 0.0, other_payments: float = 0.0,
                    months_remaining: int = 0) -> dict:
    gross = wages + investment_income
    taxable_income = max(0.0, gross - profile.standard_deduction)
    estimated_tax = estimate_federal_tax(taxable_income, profile.federal_brackets) \
        + gross * profile.state_rate
    paid = withheld_ytd + other_payments
    balance_due = round(estimated_tax - paid, 2)
    monthly = round(balance_due / months_remaining, 2) if months_remaining else None
    return {
        "estimated_tax": round(estimated_tax, 2),
        "withheld_plus_payments": round(paid, 2),
        "balance_due": balance_due,
        "suggested_monthly_withholding_increase": monthly,
    }


def investment_income(transactions: list[Transaction],
                      income_categories=("Dividends", "Interest", "Capital Gains")) -> float:
    cats = {c.lower() for c in income_categories}
    total = sum(t.amount for t in transactions
                if t.amount > 0 and (t.category or "").lower() in cats)
    return round(total, 2)


def harvesting_candidates(holdings: list[Holding], taxable_account_ids: set[str]) -> list[dict]:
    out = []
    for h in holdings:
        if (h.account_id in taxable_account_ids and h.cost_basis is not None
                and h.market_value < h.cost_basis):
            out.append({
                "symbol": h.symbol, "account_id": h.account_id,
                "market_value": round(h.market_value, 2), "cost_basis": round(h.cost_basis, 2),
                "unrealized_loss": round(h.market_value - h.cost_basis, 2),
                "wash_sale_caution": True,
            })
    out.sort(key=lambda r: r["unrealized_loss"])
    return out
