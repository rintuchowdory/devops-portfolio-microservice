from fastapi import APIRouter, Query
from typing import Optional
from app.services.store import get_logs
from app.models.schemas import LogResponse

router = APIRouter()

@router.get("/logs", response_model=LogResponse, summary="Fetch logs with filters")
async def fetch_logs(
    service: Optional[str] = Query(None, description="Filter by service name"),
    level: Optional[str] = Query(None, description="INFO | WARN | ERROR | DEBUG"),
    limit: int = Query(50, ge=1, le=500, description="Max entries to return"),
):
    return get_logs(service=service, level=level, limit=limit)
