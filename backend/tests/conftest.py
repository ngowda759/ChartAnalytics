"""Shared pytest fixtures.

Clears the in-process caches between tests so cached analyses (decision
signals, agent analysis) never leak across tests or across an hour-boundary
seed change mid-run.

Tests run OFFLINE in explicit mock/dev mode so they never hit the network
and remain deterministic; production paths use real (yfinance/broker) data.
Imports are deferred into the fixture body so collecting this conftest never
requires ``app`` to be importable at module load (CI runs bare ``pytest``
without ``backend/`` on ``sys.path`` until after collection).
"""
import pytest


@pytest.fixture(autouse=True)
def _reset_caches():
    from app.services import (
        decision_signals,
        market_data,
        market_service,
        trading_agents,
    )

    # Force the explicit mock/dev provider for the whole test session so unit
    # tests are offline + deterministic. Individual tests override to yfinance
    # via market_data.override_market_data_provider("yfinance") when needed.
    market_data.override_market_data_provider("mock")
    market_data.clear_market_data_cache()
    # Reset the singleton market service so provider changes take effect.
    market_service._market_service = None

    trading_agents.invalidate_analysis_cache()
    decision_signals.invalidate_signals_cache()
    yield

    market_data.override_market_data_provider(None)
    market_data.clear_market_data_cache()
    market_service._market_service = None
    trading_agents.invalidate_analysis_cache()
    decision_signals.invalidate_signals_cache()
