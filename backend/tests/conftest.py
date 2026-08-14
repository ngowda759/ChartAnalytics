"""Shared pytest fixtures.

Clears the in-process caches between tests so cached analyses (decision
signals, agent analysis) never leak across tests or across an hour-boundary
seed change mid-run.
"""
import pytest

from app.services import decision_signals, trading_agents


@pytest.fixture(autouse=True)
def _reset_caches():
    trading_agents.invalidate_analysis_cache()
    decision_signals.invalidate_signals_cache()
    yield
    trading_agents.invalidate_analysis_cache()
    decision_signals.invalidate_signals_cache()
