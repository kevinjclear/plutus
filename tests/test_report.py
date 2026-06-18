from plutus.report import render_report


def _data():
    return {
        "generated_at": "2026-06-17T08:00:00",
        "net_worth": {"net_worth": 51300.0, "total_assets": 52500.0, "total_liabilities": 1200.0},
        "monthly_cash_flow": {"2026-06": {"income": 3000.0, "expense": -142.5, "net": 2857.5}},
        "allocation": {"us_large_growth": {"value": 5000.0, "weight": 0.5},
                       "gold": {"value": 4000.0, "weight": 0.4},
                       "needs_classification": {"value": 1000.0, "weight": 0.1}},
        "strategy_gap": [
            {"bucket": "gold", "current_weight": 0.4, "target_weight": 0.0,
             "delta_weight": 0.4, "current_value": 4000.0, "delta_value": 4000.0},
        ],
        "harvesting": [
            {"symbol": "GLD", "account_id": "sch", "market_value": 4000.0, "cost_basis": 4600.0,
             "unrealized_loss": -600.0, "wash_sale_caution": True},
        ],
        "needs_attention": ["Unmapped account: 'Wealthfront Individual'"],
        "withholding": {"estimated_tax": 10432.0, "withheld_plus_payments": 8432.0,
                        "balance_due": 2000.0, "suggested_monthly_withholding_increase": 500.0},
    }


def test_report_has_disclaimer_and_sections():
    md = render_report(_data())
    assert "not financial" in md.lower() and "cpa" in md.lower()
    assert "# " in md                                   # has a title
    assert "Net worth" in md and "$51,300" in md
    assert "Allocation" in md and "Strategy" in md
    assert "needs_classification" in md                 # surfaced, not hidden
    assert "GLD" in md and "wash" in md.lower()          # harvesting + caution
    assert "$2,000" in md and "500" in md                # balance due + monthly fix
    assert "Wealthfront Individual" in md                # needs attention surfaced


def test_report_without_withholding_omits_tax_balance():
    data = _data(); data["withholding"] = None
    md = render_report(data)
    assert "Balance due" not in md
