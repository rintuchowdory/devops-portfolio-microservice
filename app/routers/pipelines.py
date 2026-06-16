from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.store import get_pipelines, trigger_pipeline
from app.models.schemas import PipelineListResponse, Pipeline, StageStatus, TriggerResponse

router = APIRouter()


@router.get("/pipelines", response_model=PipelineListResponse, summary="List all pipelines")
async def list_pipelines(
    status: Optional[StageStatus] = Query(None),
    service: Optional[str] = Query(None),
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


@router.get("/pipelines/{pipeline_id}", response_model=Pipeline)
async def get_pipeline(pipeline_id: str):
    data = get_pipelines()
    for p in data.pipelines:
        if p.id == pipeline_id:
            return p
    raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")


@router.post("/pipelines/{pipeline_id}/trigger", response_model=TriggerResponse, status_code=202)
async def trigger_pipeline_run(pipeline_id: str):
    result = trigger_pipeline(pipeline_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")
    return TriggerResponse(
        pipeline_id=result["pipeline_id"],
        status="queued",
        message=f"Pipeline for '{result['service']}' queued successfully",
        triggered_at=result["triggered_at"],
    )
