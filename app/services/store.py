"""
Centralized in-memory data store.
Simulates realistic drift so the dashboard feels live.
Replace each method body with real DB / Prometheus / K8s API calls in production.
"""
from __future__ import annotations
import random
import time
from datetime import datetime, timezone
from typing import List
from app.models.schemas import (
    Service, ServiceStats, ServiceStatus, ServiceListResponse,
    Pipeline, PipelineStage, PipelineListResponse, StageStatus,
    K8sNamespace, Pod, PodStatus, K8sResponse,
    LogEntry, LogLevel, LogResponse,
    DashboardSummary, ServiceMetric, TimeSeriesPoint,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _ts_series(base: float, spread: float, points: int = 10) -> List[TimeSeriesPoint]:
    series = []
    for i in range(points):
        val = round(max(0.0, base + random.uniform(-spread, spread)), 1)
        t = datetime.now(timezone.utc).replace(
            minute=datetime.now(timezone.utc).minute - (points - i)
        ).strftime("%H:%M")
        series.append(TimeSeriesPoint(ts=t, value=val))
    return series


# ── SERVICE DATA ──────────────────────────────────────────────────────────────

_SERVICES_BASE = [
    dict(
        id="api-gateway", name="api-gateway",
        description="Edge proxy & rate limiter",
        stack="Kong 3.4 · Nginx",
        version="v3.4.1", status=ServiceStatus.UP,
        req_per_min=2400, uptime=99.98, p50=38, p95=90, p99=140,
        replicas=3, cpu=24.0, mem=31.0, err=0.01,
        last_deploy="2h ago", port=8000, namespace="production",
        tags=["gateway", "proxy", "edge"],
    ),
    dict(
        id="auth-service", name="auth-service",
        description="JWT · OAuth2 · RBAC",
        stack="FastAPI · PostgreSQL · Redis",
        version="v2.1.0", status=ServiceStatus.UP,
        req_per_min=890, uptime=99.95, p50=62, p95=120, p99=200,
        replicas=2, cpu=45.0, mem=52.0, err=0.05,
        last_deploy="4h ago", port=8001, namespace="production",
        tags=["auth", "security", "jwt"],
    ),
    dict(
        id="payment-svc", name="payment-svc",
        description="Stripe gateway · billing",
        stack="FastAPI · Redis · PostgreSQL",
        version="v1.8.3", status=ServiceStatus.DEGRADED,
        req_per_min=340, uptime=97.4, p50=210, p95=480, p99=900,
        replicas=2, cpu=71.0, mem=91.0, err=2.4,
        last_deploy="6h ago", port=8002, namespace="production",
        tags=["payment", "billing", "stripe"],
    ),
    dict(
        id="user-service", name="user-service",
        description="User profiles · preferences",
        stack="FastAPI · PostgreSQL",
        version="v3.0.2", status=ServiceStatus.UP,
        req_per_min=620, uptime=99.9, p50=55, p95=110, p99=180,
        replicas=2, cpu=38.0, mem=44.0, err=0.02,
        last_deploy="1d ago", port=8003, namespace="production",
        tags=["users", "profiles"],
    ),
    dict(
        id="notification-svc", name="notification-svc",
        description="Email · SMS · Webhooks",
        stack="FastAPI · RabbitMQ · SMTP",
        version="v1.4.0", status=ServiceStatus.UP,
        req_per_min=180, uptime=99.7, p50=88, p95=200, p99=350,
        replicas=1, cpu=18.0, mem=26.0, err=0.1,
        last_deploy="3d ago", port=8004, namespace="production",
        tags=["notifications", "email", "messaging"],
    ),
    dict(
        id="inventory-svc", name="inventory-svc",
        description="Stock · SKU management",
        stack="FastAPI · MongoDB",
        version="v2.2.1", status=ServiceStatus.UP,
        req_per_min=450, uptime=99.85, p50=72, p95=145, p99=220,
        replicas=2, cpu=52.0, mem=48.0, err=0.03,
        last_deploy="12h ago", port=8005, namespace="production",
        tags=["inventory", "stock", "mongodb"],
    ),
]


def get_services() -> ServiceListResponse:
    svcs: List[Service] = []
    for b in _SERVICES_BASE:
        # simulate small live drift
        cpu = round(min(100, b["cpu"] + random.uniform(-3, 3)), 1)
        mem = round(min(100, b["mem"] + random.uniform(-2, 2)), 1)
        req = max(0, b["req_per_min"] + random.randint(-30, 30))
        svcs.append(Service(
            id=b["id"], name=b["name"],
            description=b["description"],
            stack=b["stack"], version=b["version"],
            status=b["status"],
            stats=ServiceStats(
                req_per_min=req,
                uptime_pct=b["uptime"],
                p50_ms=b["p50"], p95_ms=b["p95"], p99_ms=b["p99"],
                replicas=b["replicas"],
                cpu_pct=cpu, mem_pct=mem,
                error_rate_pct=b["err"],
            ),
            last_deploy=b["last_deploy"],
            port=b["port"],
            namespace=b["namespace"],
            tags=b["tags"],
        ))
    up = sum(1 for s in svcs if s.status == ServiceStatus.UP)
    deg = sum(1 for s in svcs if s.status == ServiceStatus.DEGRADED)
    down = sum(1 for s in svcs if s.status == ServiceStatus.DOWN)
    return ServiceListResponse(total=len(svcs), up=up, degraded=deg, down=down, services=svcs)


def get_service(service_id: str) -> Service | None:
    result = get_services()
    for s in result.services:
        if s.id == service_id:
            return s
    return None


# ── PIPELINE DATA ─────────────────────────────────────────────────────────────

def get_pipelines() -> PipelineListResponse:
    pipelines = [
        Pipeline(
            id="pipe-001", service="api-gateway",
            branch="main ← feat/rate-limit",
            commit_sha="d817832", commit_msg="Fix rate limiter config",
            author="rintuchowdory", status=StageStatus.PASSED,
            triggered_at="10 min ago", duration_sec=175,
            stages=[
                PipelineStage(name="Build", status=StageStatus.PASSED, duration_sec=72),
                PipelineStage(name="Unit Tests", status=StageStatus.PASSED, duration_sec=43),
                PipelineStage(name="Docker Push", status=StageStatus.PASSED, duration_sec=28),
                PipelineStage(name="Deploy → Prod", status=StageStatus.PASSED, duration_sec=55),
            ],
        ),
        Pipeline(
            id="pipe-002", service="auth-service",
            branch="main ← fix/token-expiry",
            commit_sha="a1b2c3d", commit_msg="Fix JWT expiry edge case",
            author="rintuchowdory", status=StageStatus.RUNNING,
            triggered_at="2 min ago", duration_sec=None,
            stages=[
                PipelineStage(name="Build", status=StageStatus.PASSED, duration_sec=58),
                PipelineStage(name="Unit Tests", status=StageStatus.PASSED, duration_sec=31),
                PipelineStage(name="Docker Push", status=StageStatus.RUNNING),
                PipelineStage(name="Deploy → Prod", status=StageStatus.QUEUED),
            ],
        ),
        Pipeline(
            id="pipe-003", service="payment-svc",
            branch="main ← hotfix/mem-leak",
            commit_sha="f9e8d7c", commit_msg="Patch memory leak in Stripe handler",
            author="rintuchowdory", status=StageStatus.FAILED,
            triggered_at="45 min ago", duration_sec=124,
            stages=[
                PipelineStage(name="Build", status=StageStatus.PASSED, duration_sec=64),
                PipelineStage(name="Integration Tests", status=StageStatus.FAILED, duration_sec=60),
                PipelineStage(name="Docker Push", status=StageStatus.SKIPPED),
                PipelineStage(name="Deploy → Prod", status=StageStatus.SKIPPED),
            ],
        ),
    ]
    running = sum(1 for p in pipelines if p.status == StageStatus.RUNNING)
    passed = sum(1 for p in pipelines if p.status == StageStatus.PASSED)
    failed = sum(1 for p in pipelines if p.status == StageStatus.FAILED)
    return PipelineListResponse(
        total=len(pipelines), running=running, passed=passed, failed=failed,
        pipelines=pipelines,
    )


# ── KUBERNETES DATA ───────────────────────────────────────────────────────────

def _make_pods(healthy: int, warning: int = 0, dead: int = 0, prefix: str = "pod") -> List[Pod]:
    pods = []
    for i in range(healthy):
        pods.append(Pod(name=f"{prefix}-{i+1}", status=PodStatus.HEALTHY,
                        restarts=random.randint(0, 2), age="2d"))
    for i in range(warning):
        pods.append(Pod(name=f"{prefix}-w{i+1}", status=PodStatus.WARNING,
                        restarts=random.randint(3, 8), age="1d"))
    for i in range(dead):
        pods.append(Pod(name=f"{prefix}-d{i+1}", status=PodStatus.DEAD,
                        restarts=random.randint(10, 30), age="6h"))
    return pods


def get_kubernetes() -> K8sResponse:
    namespaces = [
        K8sNamespace(
            id="ns-prod", namespace="production", cluster="prod-cluster",
            cpu_pct=round(64 + random.uniform(-4, 4), 1),
            mem_pct=round(71 + random.uniform(-3, 3), 1),
            pods=_make_pods(5, 1, 0, "prod"),
            services_count=6, ingresses=2, pvcs=4,
        ),
        K8sNamespace(
            id="ns-staging", namespace="staging", cluster="staging-cluster",
            cpu_pct=round(31 + random.uniform(-3, 3), 1),
            mem_pct=round(44 + random.uniform(-3, 3), 1),
            pods=_make_pods(4, 0, 0, "stage"),
            services_count=6, ingresses=1, pvcs=2,
        ),
        K8sNamespace(
            id="ns-monitoring", namespace="monitoring", cluster="obs-stack",
            cpu_pct=round(22 + random.uniform(-2, 2), 1),
            mem_pct=round(58 + random.uniform(-3, 3), 1),
            pods=_make_pods(3, 0, 0, "obs"),
            services_count=3, ingresses=1, pvcs=3,
        ),
        K8sNamespace(
            id="ns-portfolio", namespace="devops-portfolio", cluster="portfolio-ns",
            cpu_pct=round(12 + random.uniform(-2, 2), 1),
            mem_pct=round(28 + random.uniform(-2, 2), 1),
            pods=_make_pods(2, 0, 0, "port"),
            services_count=2, ingresses=1, pvcs=1,
        ),
    ]
    all_pods = [p for ns in namespaces for p in ns.pods]
    healthy = sum(1 for p in all_pods if p.status == PodStatus.HEALTHY)
    return K8sResponse(
        total_namespaces=len(namespaces),
        total_pods=len(all_pods),
        healthy_pods=healthy,
        namespaces=namespaces,
    )


# ── METRICS DATA ──────────────────────────────────────────────────────────────

def get_service_metrics(service_id: str) -> ServiceMetric | None:
    svc = get_service(service_id)
    if not svc:
        return None
    return ServiceMetric(
        service_id=service_id,
        req_per_min=_ts_series(svc.stats.req_per_min, 80),
        latency_p50=_ts_series(svc.stats.p50_ms, 15),
        error_rate=_ts_series(svc.stats.error_rate_pct, 0.5),
        cpu=_ts_series(svc.stats.cpu_pct, 5),
        mem=_ts_series(svc.stats.mem_pct, 4),
    )


def get_dashboard_summary() -> DashboardSummary:
    svc_data = get_services()
    pipe_data = get_pipelines()
    avg_lat = int(sum(s.stats.p50_ms for s in svc_data.services) / len(svc_data.services))
    total_req = sum(s.stats.req_per_min for s in svc_data.services)
    avg_err = round(sum(s.stats.error_rate_pct for s in svc_data.services) / len(svc_data.services), 2)
    return DashboardSummary(
        services_up=svc_data.up,
        services_degraded=svc_data.degraded,
        services_down=svc_data.down,
        avg_response_ms=avg_lat,
        deployments_today=7,
        deployments_passed=pipe_data.passed + 4,
        deployments_failed=pipe_data.failed,
        active_alerts=2,
        total_req_per_min=total_req,
        overall_error_rate=avg_err,
        generated_at=_now(),
    )


# ── LOG DATA ──────────────────────────────────────────────────────────────────

_LOG_POOL = [
    ("api-gateway",     LogLevel.INFO,  "GET /api/v1/products 200 38ms",             "prod-1"),
    ("auth-service",    LogLevel.INFO,  "Token validated uid=u_9f2a3b",              "prod-2"),
    ("payment-svc",     LogLevel.WARN,  "Memory usage 91% — GC pressure detected",   "prod-3"),
    ("user-service",    LogLevel.INFO,  "POST /users/profile 201 55ms",              "prod-4"),
    ("payment-svc",     LogLevel.ERROR, "Integration test failed: stripe mock timeout", "prod-3"),
    ("api-gateway",     LogLevel.INFO,  "Rate limiter reset for 192.168.1.1",        "prod-1"),
    ("notification-svc",LogLevel.INFO,  "Email dispatched to chowdoryrintu60@gmail.com", "prod-5"),
    ("inventory-svc",   LogLevel.INFO,  "Stock sync complete — 2841 items",          "prod-6"),
    ("payment-svc",     LogLevel.WARN,  "Retrying DB connection (attempt 2/3)",      "prod-3"),
    ("auth-service",    LogLevel.INFO,  "Docker push initiated sha256:a1b2c3",       "prod-2"),
    ("api-gateway",     LogLevel.INFO,  "GET /api/v1/orders 200 41ms",              "prod-1"),
    ("inventory-svc",   LogLevel.INFO,  "GET /stock/sku-441 200 68ms",              "prod-6"),
    ("user-service",    LogLevel.WARN,  "Slow query detected: 340ms",               "prod-4"),
    ("auth-service",    LogLevel.ERROR, "Failed login attempt from 10.0.0.42",      "prod-2"),
    ("api-gateway",     LogLevel.INFO,  "Health check passed for all upstreams",    "prod-1"),
]


def get_logs(
    service: str | None = None,
    level: str | None = None,
    limit: int = 50,
) -> LogResponse:
    pool = _LOG_POOL * 3  # replicate for variety
    random.shuffle(pool)
    entries: List[LogEntry] = []
    for i, (svc, lvl, msg, pod) in enumerate(pool[:limit * 2]):
        if service and svc != service:
            continue
        if level and lvl.value != level.upper():
            continue
        entries.append(LogEntry(
            id=f"log-{int(time.time())}-{i}",
            timestamp=_now(),
            service=svc,
            level=lvl,
            message=msg,
            trace_id=f"trace-{random.randint(10000,99999)}",
            pod=pod,
        ))
        if len(entries) >= limit:
            break
    return LogResponse(total=len(entries), entries=entries)
