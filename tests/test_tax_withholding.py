from plutus.tax import withholding_gap, TaxProfile

MFJ = [
    {"up_to": 23200, "rate": 0.10},
    {"up_to": 94300, "rate": 0.12},
    {"up_to": None, "rate": 0.22},
]
PROFILE = TaxProfile(filing_status="married_filing_jointly", federal_brackets=MFJ,
                     standard_deduction=29200, state_rate=0.0)


def test_balance_due_reproduces_2000():
    # wages 120k - 29.2k ded = 90.8k taxable -> fed 10,432; withheld 8,432 -> owe 2,000
    g = withholding_gap(wages=120000, withheld_ytd=8432, profile=PROFILE)
    assert g["estimated_tax"] == 10432.0
    assert g["balance_due"] == 2000.0
    assert g["suggested_monthly_withholding_increase"] is None


def test_monthly_fix_spreads_balance():
    g = withholding_gap(wages=120000, withheld_ytd=8432, profile=PROFILE, months_remaining=4)
    assert g["suggested_monthly_withholding_increase"] == 500.0


def test_refund_is_negative_balance():
    g = withholding_gap(wages=120000, withheld_ytd=12000, profile=PROFILE)
    assert g["balance_due"] == -1568.0           # overpaid -> refund


def test_investment_income_increases_tax():
    base = withholding_gap(wages=120000, withheld_ytd=8432, profile=PROFILE)
    withinv = withholding_gap(wages=120000, withheld_ytd=8432, profile=PROFILE, investment_income=10000)
    assert withinv["estimated_tax"] > base["estimated_tax"]
    assert withinv["balance_due"] > base["balance_due"]
