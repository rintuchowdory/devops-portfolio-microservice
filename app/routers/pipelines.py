from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.store import get_pipelines
from app.models.schemas import PipelineListResponse, Pipeline, StageStatus

router = APIRouter()


@router.get("/pipelines", response_model=PipelineListResponse, summary="List all pipelines")
async def list_pipelines(
    status: Optional[StageStatus] = Query(None, description="Filter by status"),
    service: Optional[str] = Query(None, description="Filter by service name"),
):
    data = get_pipelines()
    pipes = data.pipelines

    if status:
        pipes = [p for p in pipes if p.status == status]
    if service:
        pipes = [p for p in pipes if p.service == service]

    return PipelineListResponse(
        total=len(pipes),
        running=sum(1 for p in pipes if p.status == StageStatus.RUNNING),
        passed=sum(1 for p in pipes if p.status == StageStatus.PASSED),
        failed=sum(1 for p in pipes if p.status == StageStatus.FAILED),
        pipelines=pipes,
    )


@router.get("/pipelines/{pipeline_id}", response_model=Pipeline, summary="Get pipeline by ID")
async def get_pipeline(pipeline_id: str):
    data = get_pipelines()
    for p in data.pipelines:
        if p.id == pipeline_id:
            return p
    raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")
