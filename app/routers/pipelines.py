from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.core.logger import logger
from app.models.schemas import (
    Pipeline,
    PipelineListResponse,
    StageStatus,
    TriggerResponse,
)
from app.services import github_ci
from app.services.store import get_pipelines, trigger_pipeline

router = APIRouter()


async def _pipelines() -> PipelineListResponse:
    """GitHub Actions when it is configured and reachable, demo store otherwise."""
    if settings.PIPELINES_SOURCE == "simulated":
        return get_pipelines()
    if settings.PIPELINES_SOURCE == "github" and not settings.GITHUB_TOKEN:
        logger.warning("PIPELINES_SOURCE=github but GITHUB_TOKEN is empty")

    live = await github_ci.get_github_pipelines()
    return live if live is not None else get_pipelines()


@router.get("/pipelines", response_model=PipelineListResponse, summary="List CI pipeline runs")
async def list_pipelines(
    status: StageStatus | None = Query(None),
    service: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
):
    data = await _pipelines()
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
        pipelines=pipes[:limit],
        source=data.source,
    )


@router.get("/pipelines/{pipeline_id}", response_model=Pipeline)
async def get_pipeline(pipeline_id: str):
    data = await _pipelines()
    for p in data.pipelines:
        if p.id == pipeline_id:
            return p
    raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")


@router.post("/pipelines/{pipeline_id}/trigger", response_model=TriggerResponse, status_code=202)
async def trigger_pipeline_run(pipeline_id: str):
    data = await _pipelines()

    if data.source == "github":
        if not any(p.id == pipeline_id for p in data.pipelines):
            raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")
        # The workflows in these repos have no workflow_dispatch trigger, and
        # pretending to queue one would be a lie the dashboard then repeats.
        raise HTTPException(
            status_code=409,
            detail=(
                "Runs shown here come from the GitHub Actions API. "
                "Trigger a real run with `git push` or `gh workflow run`."
            ),
        )

    result = trigger_pipeline(pipeline_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")
    return TriggerResponse(
        pipeline_id=result["pipeline_id"],
        status="queued",
        message=f"Pipeline for '{result['service']}' queued successfully",
        triggered_at=result["triggered_at"],
    )
