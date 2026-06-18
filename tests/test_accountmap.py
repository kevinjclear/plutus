import json

from plutus.providers.accountmap import account_number, match_meta
from plutus.providers.actual import ActualProvider


def test_account_number_extraction():
    assert account_number("Acme Brokerage (1234)") == "1234"
    # "- NNNNNN" form, and the "(k)" has no digits so the last >=3 run wins
    assert account_number("Workplace 401(k) Plan - 567890") == "567890"
    assert account_number("Rewards Card (5566)") == "5566"
    # decimals like 3.30 (runs < 3 digits) don't interfere with the account number
    assert account_number("High-Yield Savings 3.30% APY (7788)") == "7788"
    assert account_number("No digits here") is None


def test_match_meta_exact_then_account_number():
    cfg = {
        "Acme Brokerage (1234)": {"type": "brokerage"},
        "Everyday Checking (5566)": {"type": "checking"},
    }
    assert match_meta("Acme Brokerage (1234)", cfg)["type"] == "brokerage"   # exact
    # renamed in the app, same account number -> still matches by token
    assert match_meta("Acme Taxable RENAMED (1234)", cfg)["type"] == "brokerage"
    assert match_meta("Other Bank (9999)", cfg) is None
    assert match_meta("No number", cfg) is None


def test_actual_provider_matches_renamed_account(tmp_path):
    exp = tmp_path / "exp.json"
    exp.write_text(json.dumps({
        "exported_at": "2026-06-18T00:00:00Z",
        "accounts": [
            {"id": "a1", "name": "Acme Brokerage (1234)",
             "balance": 7090614, "offbudget": False, "closed": False},
        ],
        "transactions": [],
    }))
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        'accounts:\n'
        '  "Old Account Name (1234)": {institution: Acme, type: brokerage, '
        'tax_type: taxable, is_liability: false}\n'
        'defaults: {institution: Unknown, type: checking, tax_type: none, is_liability: false}\n'
    )
    p = ActualProvider(str(exp), str(cfg))
    acct = p.fetch_accounts()[0]
    # matched by the (1234) token despite the config using the old name
    assert acct.type == "brokerage" and acct.institution == "Acme"
    assert p.unmapped_account_names() == []
