"""Tests for the Decision Signals service (ported from daily_stock_analysis)."""
import pytest

from app.schemas.decision_signals import DecisionAction
from app.services import decision_signals as ds


class TestDecisionSignals:
    def test_build_signals_returns_signals(self):
        signals = ds.build_signals()
        assert signals, "dashboard must never be empty"
        for s in signals:
            assert 0 <= s.score <= 100
            assert s.action in (DecisionAction.BUY, DecisionAction.HOLD, DecisionAction.AVOID)

    def test_buy_signals_have_risk_reward(self):
        signals = ds.build_signals()
        buys = [s for s in signals if s.action == DecisionAction.BUY]
        if not buys:
            pytest.skip("no buy signals this hour")
        for s in buys:
            assert s.entry and s.stop_loss and s.target
            assert s.risk_reward is not None and s.risk_reward > 0
            assert s.stop_loss < s.entry < s.target

    def test_avoid_signals_have_no_targets(self):
        signals = ds.build_signals()
        avoids = [s for s in signals if s.action == DecisionAction.AVOID]
        for s in avoids:
            assert s.target is None
            assert s.stop_loss is None

    def test_filter_by_action(self):
        buys = ds.list_signals(action=DecisionAction.BUY, limit=200)
        assert buys
        assert all(s.action == DecisionAction.BUY for s in buys)

    def test_filter_by_min_score(self):
        signals = ds.list_signals(min_score=70, limit=200)
        assert all(s.score >= 70 for s in signals)

    def test_filter_by_strategy(self):
        signals = ds.list_signals(strategy="bull_trend", limit=200)
        assert signals
        assert all(s.strategy == "bull_trend" for s in signals)

    def test_unknown_strategy_returns_empty(self):
        assert ds.list_signals(strategy="nope", limit=10) == []

    def test_available_strategies_lists_templates(self):
        strategies = ds.available_strategies()
        assert "ma_golden_cross" in strategies
        assert "volume_breakout" in strategies

    def test_get_signal_round_trip(self):
        signals = ds.build_signals()
        if not signals:
            pytest.skip("no signals")
        target = signals[0]
        fetched = ds.get_signal(target.id)
        assert fetched is not None
        assert fetched.id == target.id
        assert ds.get_signal("does-not-exist") is None
