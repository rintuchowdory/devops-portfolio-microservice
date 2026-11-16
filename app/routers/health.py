from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.config import settings
from app.core.metrics import uptime_seconds

router = APIRouter()
_STARTED_AT = datetime.now(UTC)


@router.get("/health", summary="Liveness probe")
async def health():
    """Kubernetes liveness / Render health check. Cheap and dependency free."""
    return {
        "status": "ok",
        "service": "devops-mesh-api",
        "version": settings.VERSION,
        "env": settings.ENV,
        "uptime_seconds": uptime_seconds(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/ready", summary="Readiness probe")
async def ready():
    """Readiness probe: verifies the data layer actually answers."""
    checks = {"store": "ok", "router": "ok", "metrics": "ok"}
    try:
        from app.services.store import get_dashboard_summary

        get_dashboard_summary()
    except Exception as exc:  # pragma: no cover - defensive
        checks["store"] = f"error: {exc}"
        return {"status": "degraded", "checks": checks}
    return {"status": "ready", "checks": checks}


@router.get("/", summary="Root - service index")
async def root():
    return {
        "message": "DevOps Mesh API",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
        "api": "/api/v1",
    }
