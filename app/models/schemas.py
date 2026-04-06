from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime


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
    tags: List[str] = []


class ServiceListResponse(BaseModel):
    total: int
    up: int
    degraded: int
    down: int
    services: List[Service]


class PipelineStage(BaseModel):
    name: str
    status: StageStatus
    duration_sec: Optional[int] = None
    started_at: Optional[str] = None


class Pipeline(BaseModel):
    id: str
    service: str
    branch: str
    commit_sha: str
    commit_msg: str
    author: str
    status: StageStatus
    triggered_at: str
    duration_sec: Optional[int]
    stages: List[PipelineStage]


class PipelineListResponse(BaseModel):
    total: int
    running: int
    passed: int
    failed: int
    pipelines: List[Pipeline]


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
    pods: List[Pod]
    services_count: int
    ingresses: int
    pvcs: int


class K8sResponse(BaseModel):
    total_namespaces: int
    total_pods: int
    healthy_pods: int
    namespaces: List[K8sNamespace]


class TimeSeriesPoint(BaseModel):
    ts: str
    value: float


class ServiceMetric(BaseModel):
    service_id: str
    req_per_min: List[TimeSeriesPoint]
    latency_p50: List[TimeSeriesPoint]
    error_rate: List[TimeSeriesPoint]
    cpu: List[TimeSeriesPoint]
    mem: List[TimeSeriesPoint]


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
    trace_id: Optional[str] = None
    pod: Optional[str] = None


class LogResponse(BaseModel):
    total: int
    entries: List[LogEntry]
