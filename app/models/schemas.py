from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class ServiceStatus(str, Enum):
    UP = "up"
    DEGRADED = "degraded"
    DOWN = "down"


class StageStatus(str, Enum):
    PASSED = "passed"
    RUNNING = "running"
    FAILED = "failed"
    QUEUED = "queued"
    SKIPPED = "skipped"


class PodStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    DEAD = "dead"


class LogLevel(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    DEBUG = "DEBUG"


class ServiceStats(BaseModel):
    req_per_min: int
    uptime_pct: float
    p50_ms: int
    p95_ms: int
    p99_ms: int
    replicas: int
    cpu_pct: float
    mem_pct: float
    error_rate_pct: float


class Service(BaseModel):
    id: str
    name: str
    description: str
    stack: str
    version: str
    status: ServiceStatus
    stats: ServiceStats
    last_deploy: str
    port: int
    namespace: str
    tags: list[str] = []


class ServiceListResponse(BaseModel):
    total: int
    up: int
    degraded: int
    down: int
    services: list[Service]


class PipelineStage(BaseModel):
    name: str
    status: StageStatus
    duration_sec: int | None = None
    started_at: str | None = None


class Pipeline(BaseModel):
    id: str
    service: str
    branch: str
    commit_sha: str
    commit_msg: str
    author: str
    status: StageStatus
    triggered_at: str
    duration_sec: int | None
    stages: list[PipelineStage]
    url: str | None = None
    triggered_at_iso: str | None = None


class PipelineListResponse(BaseModel):
    total: int
    running: int
    passed: int
    failed: int
    pipelines: list[Pipeline]
    # "github" when the runs come from the Actions API, "simulated" for the demo store
    source: str = "simulated"


class Pod(BaseModel):
    name: str
    status: PodStatus
    restarts: int
    age: str


class K8sNamespace(BaseModel):
    id: str
    namespace: str
    cluster: str
    cpu_pct: float
    mem_pct: float
    pods: list[Pod]
    services_count: int
    ingresses: int
    pvcs: int


class K8sResponse(BaseModel):
    total_namespaces: int
    total_pods: int
    healthy_pods: int
    namespaces: list[K8sNamespace]


class TimeSeriesPoint(BaseModel):
    ts: str
    value: float


class ServiceMetric(BaseModel):
    service_id: str
    req_per_min: list[TimeSeriesPoint]
    latency_p50: list[TimeSeriesPoint]
    error_rate: list[TimeSeriesPoint]
    cpu: list[TimeSeriesPoint]
    mem: list[TimeSeriesPoint]


class DashboardSummary(BaseModel):
    services_up: int
    services_degraded: int
    services_down: int
    avg_response_ms: int
    deployments_today: int
    deployments_passed: int
    deployments_failed: int
    active_alerts: int
    total_req_per_min: int
    overall_error_rate: float
    generated_at: str


class LogEntry(BaseModel):
    id: str
    timestamp: str
    service: str
    level: LogLevel
    message: str
    trace_id: str | None = None
    pod: str | None = None


class LogResponse(BaseModel):
    total: int
    entries: list[LogEntry]


class TriggerResponse(BaseModel):
    pipeline_id: str
    status: str
    message: str
    triggered_at: str
