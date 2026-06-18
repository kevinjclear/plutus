"""Strategy config: bucket target weights + ticker->bucket classification."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

NEEDS_CLASSIFICATION = "needs_classification"


@dataclass
class Strategy:
    targets: dict[str, float]
    ticker_map: dict[str, str]
    # Fund look-through: split one holding across buckets. Each rule is
    # {"match_description": <substring>, "split": {bucket: weight, ...}}.
    lookthrough: list[dict] = field(default_factory=list)

    def bucket_for(self, symbol: str) -> str:
        return self.ticker_map.get((symbol or "").upper(), NEEDS_CLASSIFICATION)

    def lookthrough_for(self, holding) -> dict | None:
        """Return the matching look-through rule for a holding, or None.

        Matches a case-insensitive substring of the holding's description; used
        for funds with no usable ticker (e.g. a 401k target-date fund)."""
        desc = (getattr(holding, "name", None) or "").lower()
        for rule in self.lookthrough:
            needle = (rule.get("match_description") or "").lower()
            if needle and needle in desc:
                return rule
        return None


def load_strategy(path: str) -> Strategy:
    cfg = yaml.safe_load(Path(path).read_text()) or {}
    targets = {k: float(v) for k, v in (cfg.get("targets") or {}).items()}
    ticker_map = {k.upper(): v for k, v in (cfg.get("tickers") or {}).items()}
    lookthrough = list(cfg.get("lookthrough") or [])
    return Strategy(targets=targets, ticker_map=ticker_map, lookthrough=lookthrough)
