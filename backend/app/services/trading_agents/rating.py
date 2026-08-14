"""5-tier rating vocabulary and helpers — ported from TradingAgents (Apache-2.0).

Centralises the Buy / Overweight / Hold / Underweight / Sell scale used by
the Research Manager, Portfolio Manager, and signal extraction.
"""

from __future__ import annotations

import re

# Canonical, ordered 5-tier scale (most bullish to most bearish).
RATINGS_5_TIER: tuple[str, ...] = (
    "Buy",
    "Overweight",
    "Hold",
    "Underweight",
    "Sell",
)

_RATING_SET = {r.lower() for r in RATINGS_5_TIER}

# Matches "Rating: X" / "rating - X" / "Rating: **X**" — tolerates markdown
# bold wrappers and either a colon or hyphen separator.
_RATING_LABEL_RE = re.compile(r"rating.*?[:\-][\s*]*(\w+)", re.IGNORECASE)

# Numeric score → rating band. Matches the framework's commit-to-a-side
# guidance: Hold is reserved for genuinely balanced evidence.
_SCORE_BANDS = (
    (70, "Buy"),
    (60, "Overweight"),
    (40, "Hold"),
    (30, "Underweight"),
    (0, "Sell"),
)


def parse_rating(text: str, default: str = "Hold") -> str:
    """Heuristically extract a 5-tier rating from prose text.

    Two-pass strategy:
    1. Look for an explicit "Rating: X" label (tolerant of markdown bold).
    2. Fall back to the first 5-tier rating word found anywhere in the text.
    """
    for line in text.splitlines():
        m = _RATING_LABEL_RE.search(line)
        if m and m.group(1).lower() in _RATING_SET:
            return m.group(1).capitalize()

    for line in text.splitlines():
        for word in line.lower().split():
            clean = word.strip("*:.,")
            if clean in _RATING_SET:
                return clean.capitalize()

    return default


def rating_for_score(score: int) -> str:
    """Map a 0-100 bullishness score onto the 5-tier scale."""
    clamped = max(0, min(100, score))
    for threshold, rating in _SCORE_BANDS:
        if clamped >= threshold:
            return rating
    return "Hold"


def action_for_rating(rating: str) -> str:
    """Collapse the 5-tier rating into the Trader's 3-tier action."""
    r = rating.lower()
    if r in ("buy", "overweight"):
        return "Buy"
    if r in ("underweight", "sell"):
        return "Sell"
    return "Hold"


def rating_sign(rating: str) -> int:
    """Signed bullishness of a rating: +2 (Buy) .. -2 (Sell)."""
    # RATINGS_5_TIER is most-bullish-first; map so Sell=-2 ... Buy=+2.
    order = {name: idx for idx, name in enumerate(reversed(RATINGS_5_TIER))}
    return order.get(rating.capitalize(), 0) - 2
