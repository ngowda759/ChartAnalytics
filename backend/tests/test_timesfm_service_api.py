import numpy as np
from fastapi.testclient import TestClient

from timesfm_service import app as timesfm_app


client = TestClient(timesfm_app.app)


def test_health_does_not_load_model():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_forecast_requires_service_token(monkeypatch):
    monkeypatch.setattr(timesfm_app, "SERVICE_TOKEN", "secret")
    response = client.post(
        "/forecast",
        json={"symbol": "NIFTY", "closes": [100.0] * 60, "horizon": 2},
    )
    assert response.status_code == 401


def test_forecast_returns_quantiles(monkeypatch):
    monkeypatch.setattr(timesfm_app, "SERVICE_TOKEN", "secret")

    class FakeModel:
        def forecast(self, horizon, inputs):
            assert horizon == 2
            assert len(inputs[0]) == 60
            points = np.asarray([[102.0, 103.0]])
            quantiles = np.zeros((1, horizon, 10))
            quantiles[:, :, 1] = 98.0
            quantiles[:, :, 9] = 108.0
            return points, quantiles

    monkeypatch.setattr(timesfm_app, "_load_model", lambda: FakeModel())
    response = client.post(
        "/forecast",
        headers={"Authorization": "Bearer secret"},
        json={"symbol": "nifty", "closes": [100.0] * 60, "horizon": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "NIFTY"
    assert payload["forecast"][0]["median"] == 102.0
    assert payload["forecast"][0]["lower"] == 98.0
    assert payload["forecast"][0]["upper"] == 108.0
