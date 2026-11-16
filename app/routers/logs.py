from fastapi import APIRouter, Query

from app.models.schemas import LogResponse
from app.services.store import get_logs

router = APIRouter()


@router.get("/logs", response_model=LogResponse, summary="Fetch logs with filters")
async def fetch_logs(
    service: str | None = Query(None, description="Filter by service name"),
    level: str | None = Query(None, description="INFO | WARN | ERROR | DEBUG"),
    limit: int = Query(50, ge=1, le=500, description="Max entries to return"),
):
    return get_logs(service=service, level=level, limit=limit)
