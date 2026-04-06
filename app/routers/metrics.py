from fastapi import APIRouter, HTTPException
from app.services.store import get_dashboard_summary, get_service_metrics
from app.models.schemas import DashboardSummary, ServiceMetric

router = APIRouter()


@router.get("/metrics/summary", response_model=DashboardSummary, summary="Dashboard summary")
async def dashboard_summary():
    return get_dashboard_summary()


@router.get(
    "/metrics/services/{service_id}",
    response_model=ServiceMetric,
    summary="Time-series metrics for a service",
)
async def service_metrics(service_id: str):
    metric = get_service_metrics(service_id)
    if not metric:
        raise HTTPException(status_code=404, detail=f"No metrics for '{service_id}'")
    return metric
