"""Rename-proof account → metadata matching.

Account display names get renamed in the source app (e.g. Actual), but the
trailing account-number token is stable (e.g. "Brokerage (1234)" or
"Workplace 401(k) Plan - 567890"). We match a config entry by exact name first,
then fall back to that account-number token, so renames don't break
classification."""
from __future__ import annotations

import re


def account_number(name: str) -> str | None:
    """Return the last run of >=3 digits in the name (the stable account-number
    token), or None if there isn't one."""
    nums = re.findall(r"\d{3,}", name or "")
    return nums[-1] if nums else None


def match_meta(name: str, accounts_map: dict) -> dict | None:
    """Find the config entry for an account: exact name, then account-number
    token. Returns the entry dict, or None if unmatched."""
    if name in accounts_map:
        return accounts_map[name]
    num = account_number(name)
    if num is not None:
        for key, meta in accounts_map.items():
            if account_number(key) == num:
                return meta
    return None
