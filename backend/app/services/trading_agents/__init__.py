"""TradingAgents-style multi-agent analysis pipeline.

Adapted from the TradingAgents framework (Apache-2.0,
github.com/TauricResearch/TradingAgents). Deterministic, offline port of the
analyst → debate → manager → trader → risk-debate → portfolio-manager graph.
"""

from app.services.cache import TTLCache
from app.services.trading_agents.pipeline import (
    analyze_symbol as _analyze_symbol,
    analyze_universe as _analyze_universe,
)
from app.services.trading_agents.rating import (
    RATINGS_5_TIER,
    action_for_rating,
    rating_for_score,
    rating_sign,
)

# The pipeline is deterministic per symbol + hour (synthetic OHLC is seeded by
# symbol+hour). Cache results for ~30 minutes so a dashboard list request does
# not re-run the full multi-agent pipeline for 30 symbols on every refresh.
_ANALYSIS_CACHE: TTLCache = TTLCache(ttl=30 * 60)
_UNIVERSE_CACHE_KEY = "universe_v1"
_AGENT_SOURCE = "synthetic"


def _tag(result):
    """Stamp the synthetic source + (non-stale) flag onto a result."""
    result.source = _AGENT_SOURCE
    result.is_stale = False
    return result


def analyze_symbol(symbol: str, name=None, base=None):
    """Cached single-symbol analysis. Falls back to a fresh run on cache miss."""
    key = ("symbol", symbol, name, base)
    cached = _ANALYSIS_CACHE.get(key)
    if cached is not None:
        return _tag(cached)
    result = _tag(_analyze_symbol(symbol, name, base))
    _ANALYSIS_CACHE.set(key, result)
    return result


def analyze_universe(limit: int = 25):
    """Cached universe analysis (the expensive list endpoint path).

    Returns the cached list when fresh; otherwise regenerates for the whole
    universe, caches it, and returns the requested ``limit`` slice. This keeps a
    dashboard refresh from recomputing the pipeline for every symbol.
    """
    all_results = _ANALYSIS_CACHE.get(_UNIVERSE_CACHE_KEY)
    if all_results is None:
        all_results = [_tag(r) for r in _analyze_universe(limit=100)]
        _ANALYSIS_CACHE.set(_UNIVERSE_CACHE_KEY, all_results)
    return all_results[:limit]


def universe_cache_age_seconds():
    """Seconds since the cached universe was written, or None if not cached."""
    import time

    entry = _ANALYSIS_CACHE._store.get(_UNIVERSE_CACHE_KEY)  # noqa: SLF001
    if entry is None:
        return None
    _, expires_at = entry
    return max(0.0, time.monotonic() - (expires_at - _ANALYSIS_CACHE._ttl))  # noqa: SLF001


def invalidate_analysis_cache():
    _ANALYSIS_CACHE.clear()


__all__ = [
    "analyze_symbol",
    "analyze_universe",
    "invalidate_analysis_cache",
    "universe_cache_age_seconds",
    "RATINGS_5_TIER",
    "action_for_rating",
    "rating_for_score",
    "rating_sign",
]
