from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.core.metrics import render_prometheus, total_requests, uptime_seconds

router = APIRouter(tags=["Observability"])


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/plain": {}}}},
)
async def prometheus_metrics():
    """Scrape target for Prometheus, VictoriaMetrics or Grafana Agent."""
    return PlainTextResponse(
        content=render_prometheus(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/metrics/json", summary="Metrics as JSON (for dashboards)")
async def metrics_json():
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "env": settings.ENV,
        "uptime_seconds": uptime_seconds(),
        "requests_total": total_requests(),
    }
