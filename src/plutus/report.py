"""Render a markdown finance report from pre-computed analysis data.

Educational only — the report opens with a disclaimer; it surfaces unclassified
holdings and unmapped accounts rather than hiding them."""
from __future__ import annotations

DISCLAIMER = (
    "> **Not financial or tax advice.** These are educational estimates from your own data. "
    "Decisions are yours; consult a CPA for filing and a fiduciary for investment advice."
)


def _money(x: float) -> str:
    return f"${x:,.0f}" if abs(x) >= 100 else f"${x:,.2f}"


def _pct(w: float) -> str:
    return f"{w * 100:.1f}%"


def render_report(data: dict) -> str:
    lines: list[str] = []
    lines.append(f"# Finance report — {data.get('generated_at', '')}")
    lines.append("")
    lines.append(DISCLAIMER)
    lines.append("")

    nw = data.get("net_worth", {})
    lines.append("## Net worth")
    lines.append(f"- **Net worth:** {_money(nw.get('net_worth', 0))}")
    lines.append(f"- Assets: {_money(nw.get('total_assets', 0))}  ·  "
                 f"Liabilities: {_money(nw.get('total_liabilities', 0))}")
    lines.append("")

    lines.append("## Cash flow (by month)")
    for ym, cf in sorted(data.get("monthly_cash_flow", {}).items()):
        lines.append(f"- **{ym}** — income {_money(cf['income'])}, "
                     f"expense {_money(cf['expense'])}, net {_money(cf['net'])}")
    lines.append("")

    lines.append("## Allocation")
    for bucket, a in sorted(data.get("allocation", {}).items(),
                            key=lambda kv: kv[1]["weight"], reverse=True):
        flag = "  ⚠️ unclassified" if bucket == "needs_classification" else ""
        lines.append(f"- {bucket}: {_pct(a['weight'])} ({_money(a['value'])}){flag}")
    lines.append("")

    lines.append("## Strategy gap (you vs. target)")
    for g in data.get("strategy_gap", []):
        verb = "over" if g["delta_weight"] > 0 else "under"
        lines.append(f"- {g['bucket']}: {_pct(g['current_weight'])} vs target "
                     f"{_pct(g['target_weight'])} — {verb} by {_pct(abs(g['delta_weight']))} "
                     f"({_money(g['delta_value'])})")
    lines.append("")

    harvesting = data.get("harvesting", [])
    if harvesting:
        lines.append("## Tax-loss harvesting candidates")
        lines.append("_Unrealized losses in taxable accounts. Wash-sale rule: do not rebuy the "
                     "same/substantially-identical security within 30 days._")
        for h in harvesting:
            lines.append(f"- {h['symbol']}: loss {_money(h['unrealized_loss'])} "
                         f"(value {_money(h['market_value'])}, basis {_money(h['cost_basis'])})")
        lines.append("")

    wh = data.get("withholding")
    if wh and wh.get("balance_due", 0) > 0:
        lines.append("## Taxes — withholding gap")
        lines.append(f"- Estimated tax: {_money(wh['estimated_tax'])}; "
                     f"withheld+paid: {_money(wh['withheld_plus_payments'])}")
        lines.append(f"- **Balance due (estimate): {_money(wh['balance_due'])}**")
        inc = wh.get("suggested_monthly_withholding_increase")
        if inc:
            lines.append(f"- To zero it out: increase withholding ~{_money(inc)}/month "
                         f"(or make a quarterly estimated payment).")
        lines.append("")

    attention = data.get("needs_attention", [])
    if attention:
        lines.append("## ⚠️ Needs attention")
        for item in attention:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines)
