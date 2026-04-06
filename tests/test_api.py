"""
Full test suite for DevOps Mesh API
Run: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── HEALTH ────────────────────────────────────────────────────────────────────

def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "docs" in r.json()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_ready():
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


# ── SERVICES ──────────────────────────────────────────────────────────────────

def test_list_services():
    r = client.get("/api/v1/services")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0
    assert "services" in data
    svc = data["services"][0]
    assert "id" in svc
    assert "stats" in svc


def test_filter_services_by_status():
    r = client.get("/api/v1/services?status=up")
    assert r.status_code == 200
    data = r.json()
    for svc in data["services"]:
        assert svc["status"] == "up"


def test_filter_services_by_namespace():
    r = client.get("/api/v1/services?namespace=production")
    assert r.status_code == 200
    for svc in r.json()["services"]:
        assert svc["namespace"] == "production"


def test_filter_services_by_tag():
    r = client.get("/api/v1/services?tag=auth")
    assert r.status_code == 200
    for svc in r.json()["services"]:
        assert "auth" in svc["tags"]


def test_get_service_by_id():
    r = client.get("/api/v1/services/api-gateway")
    assert r.status_code == 200
    assert r.json()["id"] == "api-gateway"


def test_get_service_not_found():
    r = client.get("/api/v1/services/nonexistent-svc")
    assert r.status_code == 404


# ── PIPELINES ─────────────────────────────────────────────────────────────────

def test_list_pipelines():
    r = client.get("/api/v1/pipelines")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0
    assert "pipelines" in data


def test_filter_pipelines_by_status():
    r = client.get("/api/v1/pipelines?status=failed")
    assert r.status_code == 200
    for p in r.json()["pipelines"]:
        assert p["status"] == "failed"


def test_get_pipeline_by_id():
    r = client.get("/api/v1/pipelines/pipe-001")
    assert r.status_code == 200
    assert r.json()["id"] == "pipe-001"
    assert len(r.json()["stages"]) > 0


def test_get_pipeline_not_found():
    r = client.get("/api/v1/pipelines/pipe-999")
    assert r.status_code == 404


# ── KUBERNETES ────────────────────────────────────────────────────────────────

def test_kubernetes_overview():
    r = client.get("/api/v1/kubernetes")
    assert r.status_code == 200
    data = r.json()
    assert data["total_namespaces"] > 0
    assert data["healthy_pods"] <= data["total_pods"]


def test_get_namespace():
    r = client.get("/api/v1/kubernetes/ns-prod")
    assert r.status_code == 200
    assert r.json()["id"] == "ns-prod"


def test_get_namespace_not_found():
    r = client.get("/api/v1/kubernetes/ns-fake")
    assert r.status_code == 404


# ── METRICS ───────────────────────────────────────────────────────────────────

def test_dashboard_summary():
    r = client.get("/api/v1/metrics/summary")
    assert r.status_code == 200
    data = r.json()
    assert "services_up" in data
    assert "avg_response_ms" in data
    assert "deployments_today" in data


def test_service_metrics():
    r = client.get("/api/v1/metrics/services/auth-service")
    assert r.status_code == 200
    data = r.json()
    assert data["service_id"] == "auth-service"
    assert len(data["req_per_min"]) > 0


def test_service_metrics_not_found():
    r = client.get("/api/v1/metrics/services/fake-svc")
    assert r.status_code == 404


# ── LOGS ──────────────────────────────────────────────────────────────────────

def test_fetch_logs():
    r = client.get("/api/v1/logs")
    assert r.status_code == 200
    data = r.json()
    assert "entries" in data
    assert data["total"] > 0


def test_filter_logs_by_service():
    r = client.get("/api/v1/logs?service=api-gateway")
    assert r.status_code == 200
    for entry in r.json()["entries"]:
        assert entry["service"] == "api-gateway"


def test_filter_logs_by_level():
    r = client.get("/api/v1/logs?level=ERROR")
    assert r.status_code == 200
    for entry in r.json()["entries"]:
        assert entry["level"] == "ERROR"


def test_logs_limit():
    r = client.get("/api/v1/logs?limit=5")
    assert r.status_code == 200
    assert r.json()["total"] <= 5


def test_logs_limit_too_high():
    r = client.get("/api/v1/logs?limit=9999")
    assert r.status_code == 422  # validation error


# ── RESPONSE HEADERS ──────────────────────────────────────────────────────────

def test_response_time_header():
    r = client.get("/health")
    assert "x-response-time" in r.headers


def test_404_format():
    r = client.get("/api/v1/nonexistent")
    assert r.status_code == 404
