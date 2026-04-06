from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()


@router.get("/health", summary="Liveness probe")
async def health():
    return {
        "status": "ok",
        "service": "devops-mesh-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready", summary="Readiness probe")
async def ready():
    return {"status": "ready", "checks": {"store": "ok", "router": "ok"}}


@router.get("/", summary="Root — redirect hint")
async def root():
    return {
        "message": "DevOps Mesh API",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
    }
