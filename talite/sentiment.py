"""Fast headline scan for a quick long/short read.

This is intentionally cheap: a keyword lean over recent headlines plus a pull-out
of anything that names the ticker or company. It is a confirmation layer, not the
driver - momentum decides, news nudges. The LLM (when enabled) gets these same
headlines and can weigh them with more nuance.
"""
from __future__ import annotations

BULLISH = (
    "beat", "beats", "surge", "soar", "soars", "rally", "rallies", "jump", "jumps",
    "record", "high", "upgrade", "upgraded", "raises", "raised", "growth", "strong",
    "outperform", "buyback", "wins", "win", "gains", "gain", "rebound", "boost",
    "approval", "approved", "expands", "bullish", "tops",
)
BEARISH = (
    "miss", "misses", "plunge", "plunges", "drop", "drops", "fall", "falls", "slump",
    "downgrade", "downgraded", "cuts", "cut", "warn", "warns", "warning", "weak",
    "lawsuit", "probe", "recall", "loss", "losses", "slowdown", "fears", "selloff",
    "bearish", "sinks", "tumbles", "halt", "delay", "delayed", "layoffs",
)


def quick_sentiment(headlines: list[str], ticker: str = "",
                    company: str = "") -> tuple[float, list[str]]:
    """Return (bias in -1..+1, headlines that mention the ticker/company)."""
    if not headlines:
        return 0.0, []

    pos = neg = 0
    needles = {n.lower() for n in (ticker, company.split()[0] if company else "") if n}
    relevant = []
    for h in headlines:
        low = h.lower()
        if needles and any(n in low for n in needles):
            relevant.append(h)
        pos += sum(w in low for w in BULLISH)
        neg += sum(w in low for w in BEARISH)

    total = pos + neg
    bias = 0.0 if total == 0 else (pos - neg) / total
    return round(bias, 2), relevant
