"""Tests for the Prometheus endpoint, probes and the metric middleware."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

import app.services.store as store
from app.core import metrics
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_metrics():
    metrics.reset()
    yield
    metrics.reset()


def test_prometheus_endpoint_returns_exposition_format():
    client.get("/health")
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]
    body = r.text
    assert "# TYPE http_requests_total counter" in body
    assert 'path="/health"' in body
    assert "process_uptime_seconds" in body
    assert "app_info{" in body


def test_metrics_json():
    r = client.get("/metrics/json")
    assert r.status_code == 200
    data = r.json()
    assert data["service"]
    assert data["uptime_seconds"] >= 0


def test_route_template_used_for_metrics_not_raw_path():
    client.get("/api/v1/services/api-gateway")
    body = client.get("/metrics").text
    assert 'path="/api/v1/services/{service_id}"' in body


def test_health_reports_uptime_and_env():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "uptime_seconds" in data
    assert data["env"]


def test_readiness_checks_store():
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["checks"]["store"] == "ok"


def test_error_message_is_preserved():
    r = client.get("/api/v1/services/does-not-exist")
    assert r.status_code == 404
    data = r.json()
    assert "does-not-exist" in data["error"]
    assert data["status_code"] == 404


def test_validation_error_is_json():
    r = client.get("/api/v1/logs?limit=9999")
    assert r.status_code == 422
    data = r.json()
    assert data["error"] == "Validation failed"
    assert data["details"]


def test_response_time_header():
    r = client.get("/health")
    assert r.headers["x-response-time"].endswith("ms")


def test_cors_allows_portfolio_origin():
    r = client.options(
        "/api/v1/services",
        headers={
            "Origin": "https://rintuchowdory.github.io",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "https://rintuchowdory.github.io"


class _MinuteThreeDatetime(datetime):
    """Freezes `now()` at 00:03 UTC, the case the old implementation crashed on."""

    @classmethod
    def now(cls, tz=None):  # noqa: D102
        return datetime(2026, 1, 1, 0, 3, 20, tzinfo=UTC)


def test_time_series_survives_early_minute(monkeypatch):
    monkeypatch.setattr(store, "datetime", _MinuteThreeDatetime)
    series = store._ts_series(base=100, spread=0, points=10)
    assert len(series) == 10
    # 9 minutes before 00:03 is 23:54 of the previous day, not a ValueError.
    assert series[0].ts == "23:54"
    assert series[-1].ts == "00:03"
    minutes = [int(p.ts[:2]) * 60 + int(p.ts[3:]) for p in series]
    # Chronological, one minute apart, wrapping across midnight.
    assert all((b - a) % 1440 == 1 for a, b in zip(minutes, minutes[1:], strict=False))


def test_time_series_values_are_bounded():
    series = store._ts_series(base=10, spread=50, points=20)
    assert all(point.value >= 0 for point in series)
