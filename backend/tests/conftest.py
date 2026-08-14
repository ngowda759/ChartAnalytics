"""Shared pytest fixtures.

Clears the in-process caches between tests so cached analyses (decision
signals, agent analysis) never leak across tests or across an hour-boundary
seed change mid-run.

Imports are deferred into the fixture body so collecting this conftest never
requires ``app`` to be importable at module load (CI runs bare ``pytest``
without ``backend/`` on ``sys.path`` until after collection).
"""
import pytest


@pytest.fixture(autouse=True)
def _reset_caches():
    from app.services import decision_signals, trading_agents

    trading_agents.invalidate_analysis_cache()
    decision_signals.invalidate_signals_cache()
    yield
    trading_agents.invalidate_analysis_cache()
    decision_signals.invalidate_signals_cache()
