"""CORS preflight tests.

Regression for the Render incident where every OPTIONS preflight from the
Vercel frontend returned 400 "Disallowed CORS origin" because the frontend
origin (and its per-commit previews under *.vercel.app) were not in
CORS_ORIGINS. The fix adds an allow_origin_regex covering *.vercel.app.
"""
from fastapi.testclient import TestClient

from app.main import app


class TestCORSPreflight:
    def test_vercel_production_origin_allowed(self):
        client = TestClient(app)
        origin = "https://chart-analytics-theta.vercel.app"
        r = client.options(
            "/api/v1/market/indices",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == origin
        assert "GET" in r.headers["access-control-allow-methods"]
        assert r.headers["access-control-allow-credentials"] == "true"

    def test_vercel_preview_origin_allowed_by_regex(self):
        client = TestClient(app)
        origin = "https://chart-analytics-theta-abc123.vercel.app"
        r = client.options(
            "/api/v1/market/indices",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == origin

    def test_localhost_origin_allowed(self):
        client = TestClient(app)
        r = client.options(
            "/api/v1/market/indices",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.status_code == 200

    def test_disallowed_origin_rejected(self):
        client = TestClient(app)
        r = client.options(
            "/api/v1/market/indices",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.status_code == 400
        assert "Disallowed" in r.text

    def test_get_with_origin_returns_acao_header(self):
        client = TestClient(app)
        origin = "https://chart-analytics-theta.vercel.app"
        r = client.get("/api/v1/market/indices", headers={"Origin": origin})
        assert r.status_code == 200
        assert r.headers["access-control-allow-origin"] == origin
