from plutus.tax import estimate_federal_tax, TaxProfile

# 2024-style MFJ marginal brackets (placeholder figures).
MFJ = [
    {"up_to": 23200, "rate": 0.10},
    {"up_to": 94300, "rate": 0.12},
    {"up_to": 201050, "rate": 0.22},
    {"up_to": None, "rate": 0.24},
]


def test_progressive_tax_two_brackets():
    # taxable 90,800: 23,200*.10 + (90,800-23,200)*.12 = 2,320 + 8,112 = 10,432
    assert estimate_federal_tax(90800, MFJ) == 10432.0


def test_zero_income():
    assert estimate_federal_tax(0, MFJ) == 0.0


def test_into_top_bracket():
    # 250,000: 2320 + 8532 (12% of 71,100) + 23485 (22% of 106,750) + 11748 (24% of 48,950)
    # = 2320 + 8532.0 + 23485.0 + 11748.0
    assert estimate_federal_tax(250000, MFJ) == 46085.0


def test_profile_dataclass():
    p = TaxProfile(filing_status="married_filing_jointly", federal_brackets=MFJ,
                   standard_deduction=29200, state_rate=0.0)
    assert p.standard_deduction == 29200 and p.state_rate == 0.0
