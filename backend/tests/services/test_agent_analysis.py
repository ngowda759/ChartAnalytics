"""Tests for the TradingAgents-style agent analysis pipeline."""

from datetime import datetime
import math

import pytest
import sys
import os

# Add parent directory to path (matches existing test convention; no conftest.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.schemas.agent_analysis import (
    AgentAnalysisResult,
    PortfolioRating,
    TraderAction,
)
from app.services.trading_agents import (
    analyze_symbol,
    analyze_universe,
    action_for_rating,
    rating_for_score,
    rating_sign,
)
from app.services.trading_agents.analysts import (
    composite_score,
    fundamentals_analyst,
    market_analyst,
    news_analyst,
    run_analysts,
    sentiment_analyst,
)
from app.services.trading_agents.debate import investment_debate, risk_debate
from app.services.trading_agents.pipeline import _levels, _research_plan
from app.services.screener_engine import _generate_ohlc


# --- rating util ----------------------------------------------------------

def test_rating_for_score_boundaries():
    assert rating_for_score(70) == "Buy"
    assert rating_for_score(69) == "Overweight"
    assert rating_for_score(60) == "Overweight"
    assert rating_for_score(59) == "Hold"
    assert rating_for_score(40) == "Hold"
    assert rating_for_score(39) == "Underweight"
    assert rating_for_score(30) == "Underweight"
    assert rating_for_score(29) == "Sell"
    assert rating_for_score(0) == "Sell"
    assert rating_for_score(100) == "Buy"


def test_rating_for_score_clamps_out_of_range():
    assert rating_for_score(150) == "Buy"
    assert rating_for_score(-5) == "Sell"


def test_action_for_rating_collapses_to_three_tier():
    assert action_for_rating("Buy") == "Buy"
    assert action_for_rating("Overweight") == "Buy"
    assert action_for_rating("Hold") == "Hold"
    assert action_for_rating("Underweight") == "Sell"
    assert action_for_rating("Sell") == "Sell"


def test_rating_sign_ordered_bullish_to_bearish():
    assert rating_sign("Buy") == 2
    assert rating_sign("Overweight") == 1
    assert rating_sign("Hold") == 0
    assert rating_sign("Underweight") == -1
    assert rating_sign("Sell") == -2


# --- analysts -------------------------------------------------------------

def _candles():
    return _generate_ohlc("TEST", 1000.0)


def test_run_analysts_returns_four_roles():
    candles = _candles()
    analysts = run_analysts(candles)
    roles = [a.role for a in analysts]
    assert roles == [
        "Market Analyst",
        "Fundamentals Analyst",
        "News Analyst",
        "Sentiment Analyst",
    ]


def test_analyst_scores_in_range():
    candles = _candles()
    for analyst in run_analysts(candles):
        assert 0 <= analyst.score <= 100
        assert analyst.summary
        assert isinstance(analyst.key_points, list)


def test_market_analyst_has_key_points():
    candles = _candles()
    a = market_analyst(candles)
    assert a.role == "Market Analyst"
    assert len(a.key_points) >= 1


def test_composite_score_weighted():
    candles = _candles()
    analysts = run_analysts(candles)
    score, names = composite_score(analysts)
    assert 0 <= score <= 100
    assert "Market Analyst" in names


def test_analysts_with_insufficient_history_dont_crash():
    from app.services.screener_engine import Candle
    from datetime import datetime as dt

    few = [
        Candle(date=dt.utcnow(), open=10, high=11, low=9, close=10, volume=100)
        for _ in range(5)
    ]
    for a in run_analysts(few):
        assert 0 <= a.score <= 100


def test_candles_for_drops_nan_close_rows(monkeypatch):
    """Regression: yfinance occasionally returns OHLCV rows with NaN closes
    (halted sessions). Those rows must be dropped at the unified resolver so
    downstream analysts never hit `ValueError: cannot convert float NaN to
    integer` (the production agent-analysis 500)."""
    from app.services import market_data, screener_engine
    from app.services.screener_engine import Candle
    from datetime import datetime as dt

    candles = [
        Candle(
            date=dt.utcnow(),
            open=100.0,
            high=101.0,
            low=99.0,
            close=(100.0 if i % 7 else float("nan")),
            volume=1000,
        )
        for i in range(60)
    ]
    monkeypatch.setattr(market_data, "is_mock_mode", lambda: False)
    monkeypatch.setattr(
        market_data, "get_real_candles", lambda *a, **k: (candles, "yfinance")
    )

    resolved, src = screener_engine.candles_for("RELIANCE")
    assert src == "yfinance"
    assert resolved is not None
    assert len(resolved) < 60, "NaN rows must be dropped"
    assert all(c.close is not None and math.isfinite(c.close) for c in resolved)


def test_candles_for_returns_none_when_all_closes_nan(monkeypatch):
    """A symbol with only NaN closes yields (None, source) -> callers surface
    a truthful unavailable state instead of crashing."""
    from app.services import market_data, screener_engine
    from app.services.screener_engine import Candle
    from datetime import datetime as dt

    candles = [
        Candle(date=dt.utcnow(), open=1.0, high=1.0, low=1.0, close=float("nan"), volume=100)
        for _ in range(60)
    ]
    monkeypatch.setattr(market_data, "is_mock_mode", lambda: False)
    monkeypatch.setattr(
        market_data, "get_real_candles", lambda *a, **k: (candles, "yfinance")
    )

    resolved, src = screener_engine.candles_for("PREMIERENE")
    assert resolved is None
    assert src == "yfinance"


# --- debate ---------------------------------------------------------------

def test_investment_debate_winner_consistent_with_composite():
    candles = _candles()
    analysts = run_analysts(candles)
    composite, _ = composite_score(analysts)
    debate = investment_debate(analysts, composite)
    assert debate.winner in ("bull", "bear")
    if composite >= 50:
        assert debate.winner == "bull"
    else:
        assert debate.winner == "bear"
    assert len(debate.turns) == 2


def test_risk_debate_three_speakers():
    candles = _candles()
    analysts = run_analysts(candles)
    composite, _ = composite_score(analysts)
    from app.services.trading_agents.rating import action_for_rating

    action = action_for_rating(rating_for_score(composite))
    debate = risk_debate(analysts, composite, action)
    speakers = [t.speaker for t in debate.turns]
    assert speakers == [
        "Aggressive Risk Analyst",
        "Conservative Risk Analyst",
        "Neutral Risk Analyst",
    ]
    assert debate.winner in ("aggressive", "conservative", "neutral")


# --- pipeline -------------------------------------------------------------

def test_research_plan_uses_composite_rating():
    candles = _candles()
    analysts = run_analysts(candles)
    composite, _ = composite_score(analysts)
    plan = _research_plan(composite, analysts)
    assert plan.recommendation.value == rating_for_score(composite)
    assert plan.rationale
    assert plan.strategic_actions


def test_levels_buy_sell_hold():
    candles = _candles()
    entry, stop, target = _levels(candles, "Buy")
    assert entry > stop
    assert target > entry
    entry, stop, target = _levels(candles, "Sell")
    assert entry < stop
    assert target < entry
    entry, stop, target = _levels(candles, "Hold")
    assert stop is None and target is None


def test_analyze_symbol_full_structure():
    result = analyze_symbol("RELIANCE")
    assert isinstance(result, AgentAnalysisResult)
    assert result.symbol == "RELIANCE"
    assert result.name
    assert isinstance(result.timestamp, datetime)
    assert len(result.analysts) == 4
    assert len(result.investment_debate.turns) == 2
    assert len(result.risk_debate.turns) == 3
    assert isinstance(result.final_decision.rating, PortfolioRating)
    assert isinstance(result.trader_proposal.action, TraderAction)
    assert 0.0 <= result.confidence <= 1.0


def test_analyze_symbol_custom_base():
    result = analyze_symbol("CUSTOM", name="Custom Co", base=500.0)
    assert result.symbol == "CUSTOM"
    assert result.name == "Custom Co"
    assert result.trader_proposal.entry_price is not None


def test_analyze_symbol_unknown_falls_back_to_default_base():
    result = analyze_symbol("UNKNOWNXYZ")
    assert result.symbol == "UNKNOWNXYZ"
    assert result.trader_proposal.entry_price is not None


def test_analyze_symbol_action_matches_rating():
    result = analyze_symbol("TATASTEEL")
    rating = result.final_decision.rating
    action = result.trader_proposal.action.value
    if rating in (PortfolioRating.BUY, PortfolioRating.OVERWEIGHT):
        assert action == "Buy"
    elif rating in (PortfolioRating.SELL, PortfolioRating.UNDERWEIGHT):
        assert action == "Sell"
    else:
        assert action == "Hold"


def test_analyze_universe_returns_sorted_results():
    results = analyze_universe(limit=10)
    assert len(results) == 10
    signs = [rating_sign(r.final_decision.rating.value) for r in results]
    assert signs == sorted(signs, reverse=True)


def test_analyze_universe_full_universe():
    from app.services.screener_engine import _UNIVERSE

    results = analyze_universe(limit=1000)
    assert len(results) == len(_UNIVERSE)
    for r in results:
        assert r.symbol in [m["symbol"] for m in _UNIVERSE]


def test_analyze_universe_limit_respected():
    assert len(analyze_universe(limit=5)) == 5
    assert len(analyze_universe(limit=3)) == 3


def test_universe_has_all_rating_categories():
    results = analyze_universe()
    ratings = {r.final_decision.rating.value for r in results}
    # The deterministic universe should span both bullish and bearish ends.
    assert ratings & {"Buy", "Overweight"}
    assert ratings & {"Hold"}
    assert ratings & {"Underweight", "Sell"}
