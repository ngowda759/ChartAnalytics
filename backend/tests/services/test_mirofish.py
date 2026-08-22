"""Tests for the MiroFish swarm-prediction engine and its integrations.

The conftest autouse fixture forces the explicit mock provider, so all
predictions here are offline, deterministic, and tagged source="mock".
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.predictions import SwarmDirection
from app.services import mirofish
from app.services.mirofish import engine


class TestSwarmEngine:
    def test_seed_features_bounded(self):
        from app.services.screener_engine import candles_for

        candles, _ = candles_for("RELIANCE")
        seed = engine.extract_seed(candles)
        for value in (seed.trend, seed.momentum, seed.volume_flow, seed.price_position, seed.drift):
            assert -1.0 <= value <= 1.0
        assert seed.volatility_pct >= 0
        assert seed.last_close > 0
        assert seed.atr > 0

    def test_swarm_size_and_personas(self):
        swarm = engine.build_swarm("RELIANCE")
        assert len(swarm) == engine.SWARM_SIZE
        personas = {a.persona for a in swarm}
        assert len(personas) == 6, "expected all six persona archetypes"
        for agent in swarm:
            assert 0.0 <= agent.herd <= 0.95
            assert 0.0 < agent.memory <= 1.0

    def test_swarm_deterministic_per_symbol_hour(self):
        a = engine.build_swarm("TCS")
        b = engine.build_swarm("TCS")
        assert [(x.persona, x.aggressiveness, x.herd) for x in a] == [
            (x.persona, x.aggressiveness, x.herd) for x in b
        ]

    def test_simulation_round_counts_sum_to_swarm(self):
        from app.services.screener_engine import candles_for

        candles, _ = candles_for("INFY")
        seed = engine.extract_seed(candles)
        swarm = engine.build_swarm("INFY")
        rounds, consensus = engine.simulate(swarm, seed)
        assert len(rounds) == engine.SIMULATION_ROUNDS
        for snap in rounds:
            assert snap.bullish_pct + snap.bearish_pct + snap.neutral_pct == pytest.approx(100.0, abs=0.5)
            assert -1.0 <= snap.consensus <= 1.0
        assert -1.0 <= consensus <= 1.0

    def test_predict_symbol_structure(self):
        p = mirofish.predict_symbol("RELIANCE")
        assert p.symbol == "RELIANCE"
        assert p.direction in set(SwarmDirection)
        assert 0 <= p.conviction <= 100
        assert 0.0 <= p.confidence <= 1.0
        assert abs(p.predicted_change_percent) <= 15.0
        assert p.agents_total == engine.SWARM_SIZE
        assert p.agents_bullish + p.agents_bearish + p.agents_neutral == p.agents_total
        assert p.current_price and p.current_price > 0
        assert p.target_price and p.target_price > 0
        assert p.target_low <= p.target_high
        assert len(p.rounds) == engine.SIMULATION_ROUNDS
        assert p.key_drivers
        assert p.report
        assert p.source == "mock"
        assert p.status == "mock"

    def test_predict_symbol_deterministic(self):
        a = mirofish.predict_symbol("HDFCBANK", use_cache=False)
        b = mirofish.predict_symbol("HDFCBANK", use_cache=False)
        assert (a.direction, a.conviction, a.predicted_change_percent, a.target_price) == (
            b.direction,
            b.conviction,
            b.predicted_change_percent,
            b.target_price,
        )

    def test_predict_universe_never_empty(self):
        results = mirofish.predict_universe(limit=10)
        assert len(results) == 10
        assert results == sorted(
            results,
            key=lambda p: (p.conviction, p.predicted_change_percent),
            reverse=True,
        )

    def test_direction_consistent_with_prediction_sign(self):
        for p in mirofish.predict_universe(limit=25):
            if p.direction == SwarmDirection.BULLISH:
                assert p.predicted_change_percent > 0
            elif p.direction == SwarmDirection.BEARISH:
                assert p.predicted_change_percent < 0

    def test_unavailable_prediction_when_no_data(self, monkeypatch):
        monkeypatch.setattr(engine, "candles_for", lambda symbol, **kw: (None, "unavailable"))
        p = mirofish.predict_symbol("NODATA", use_cache=False)
        assert p.status == "unavailable"
        assert p.source == "unavailable"
        assert p.direction == SwarmDirection.NEUTRAL
        assert p.conviction == 0
        assert "unavailable" in p.report.lower()

    def test_nan_candles_yield_unavailable(self, monkeypatch):
        """Providers sometimes return rows with NaN closes; the forecast must
        degrade to a truthful unavailable state instead of propagating NaN."""
        from datetime import datetime

        from app.services.screener_engine import Candle

        nan_candles = [
            Candle(
                date=datetime.utcnow(),
                open=1.0,
                high=1.0,
                low=1.0,
                close=float("nan"),
                volume=100,
            )
            for _ in range(50)
        ]
        monkeypatch.setattr(
            engine, "candles_for", lambda symbol, **kw: (nan_candles, "yfinance")
        )
        p = mirofish.predict_symbol("NANSYM", use_cache=False)
        assert p.status == "unavailable"
        assert p.target_price is None

    def test_summary_for_symbol_compact(self):
        s = mirofish.summary_for_symbol("TITAN")
        assert s.direction in set(SwarmDirection)
        assert 0 <= s.conviction <= 100
        assert 0.0 <= s.confidence <= 1.0
        assert s.target_price is not None


class TestPredictionsApi:
    def test_list_predictions_endpoint(self):
        client = TestClient(app)
        res = client.get("/api/v1/predictions?limit=10")
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 10
        assert len(body["results"]) == 10
        assert (
            body["bullish_count"] + body["bearish_count"] + body["neutral_count"]
            == body["total"]
        )
        assert body["source"] == "mock"

    def test_get_prediction_endpoint(self):
        client = TestClient(app)
        res = client.get("/api/v1/predictions/RELIANCE")
        assert res.status_code == 200
        body = res.json()
        assert body["symbol"] == "RELIANCE"
        assert body["status"] == "mock"
        assert len(body["rounds"]) == engine.SIMULATION_ROUNDS

    def test_get_prediction_unknown_symbol_still_predicts(self):
        # Unknown symbols resolve candles via the mock provider with a default
        # base, so the engine still returns a complete prediction.
        client = TestClient(app)
        res = client.get("/api/v1/predictions/FOOBAR")
        assert res.status_code == 200
        body = res.json()
        assert body["symbol"] == "FOOBAR"
        assert body["agents_total"] == engine.SWARM_SIZE


class TestPredictionIntegrations:
    def test_decision_signals_carry_prediction(self):
        from app.services import decision_signals

        signals = decision_signals.build_signals(use_cache=False)
        assert signals
        for s in signals:
            assert s.prediction is not None
            assert s.prediction.direction in set(SwarmDirection)
            assert 0 <= s.prediction.conviction <= 100

    def test_agent_analysis_carries_prediction(self):
        from app.services.trading_agents import analyze_symbol

        result = analyze_symbol("RELIANCE")
        assert result.prediction is not None
        assert result.prediction.direction in set(SwarmDirection)
        assert 0 <= result.prediction.conviction <= 100

    def test_scanner_results_carry_prediction(self):
        from app.services import scanner_engine

        results = scanner_engine.scan_market(min_confidence=0.0, limit=50)
        assert results
        for r in results:
            assert r.prediction is not None
            assert r.prediction.direction in set(SwarmDirection)

    def test_screener_rows_carry_prediction(self):
        from app.services import screener_engine

        widget = screener_engine.build_screener_widget("potential-breakouts")
        assert widget is not None
        assert "extra.prediction_direction" in widget.columns
        if widget.rows:
            extra = widget.rows[0].extra or {}
            assert extra.get("prediction_direction") in {d.value for d in SwarmDirection}
            assert extra.get("predicted_change_pct") is not None
            assert extra.get("prediction_conviction") is not None
