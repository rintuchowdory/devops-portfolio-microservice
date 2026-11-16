"""
Real CI data from the GitHub Actions API.

`/api/v1/pipelines` used to return invented runs. It now reads the workflow runs
of the repositories that actually ship this project, so the dashboard reports on
the delivery pipeline instead of pretending to. The demo store stays as a
fallback for when no token is configured or GitHub is unreachable, and the
response says which of the two you are looking at.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import settings
from app.core.logger import logger
from app.models.schemas import Pipeline, PipelineListResponse, PipelineStage, StageStatus

# run conclusion -> the status the dashboard understands
_CONCLUSION_MAP: dict[str, StageStatus] = {
    "success": StageStatus.PASSED,
    "failure": StageStatus.FAILED,
    "timed_out": StageStatus.FAILED,
    "startup_failure": StageStatus.FAILED,
    "cancelled": StageStatus.SKIPPED,
    "skipped": StageStatus.SKIPPED,
    "neutral": StageStatus.SKIPPED,
    "action_required": StageStatus.QUEUED,
}

_cache: dict[str, Any] = {"at": 0.0, "data": None}


def _relative(iso: str | None) -> str:
    """'3 min ago' for the dashboard, ISO stays available separately."""
    if not iso:
        return "unknown"
    try:
        then = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return iso
    seconds = max(0, int((datetime.now(UTC) - then).total_seconds()))
    if seconds < 45:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} h ago"
    return f"{seconds // 86400} d ago"


def _status_of(status: str | None, conclusion: str | None) -> StageStatus:
    if status in {"in_progress", "queued", "waiting", "pending", "requested"}:
        return StageStatus.QUEUED if status != "in_progress" else StageStatus.RUNNING
    return _CONCLUSION_MAP.get(conclusion or "", StageStatus.QUEUED)


def _repo_label(full_name: str) -> str:
    """devops-portfolio-microservice -> microservice."""
    return full_name.split("/")[-1].removeprefix("devops-portfolio-")


def _duration(start: str | None, end: str | None) -> int | None:
    if not start:
        return None
    try:
        started = datetime.fromisoformat(start.replace("Z", "+00:00"))
        finished = datetime.fromisoformat(end.replace("Z", "+00:00")) if end else datetime.now(UTC)
    except ValueError:
        return None
    return max(0, int((finished - started).total_seconds()))


def _stage_from_job(job: dict[str, Any]) -> PipelineStage:
    return PipelineStage(
        name=job.get("name") or "job",
        status=_status_of(job.get("status"), job.get("conclusion")),
        duration_sec=_duration(job.get("started_at"), job.get("completed_at")),
        started_at=job.get("started_at"),
    )


def _headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "devops-portfolio-microservice",
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
    }


async def _fetch_json(client: httpx.AsyncClient, url: str, params: dict[str, Any] | None = None):
    response = await client.get(url, params=params)
    if response.status_code == 403 or response.status_code == 429:
        remaining = response.headers.get("x-ratelimit-remaining")
        raise RuntimeError(f"GitHub rate limited the request (remaining={remaining})")
    response.raise_for_status()
    return response.json()


async def _run_to_pipeline(
    client: httpx.AsyncClient,
    repo: str,
    run: dict[str, Any],
    with_stages: bool,
) -> Pipeline:
    stages: list[PipelineStage] = []
    if with_stages:
        try:
            jobs = await _fetch_json(
                client, f"{settings.GITHUB_API_URL}/repos/{repo}/actions/runs/{run['id']}/jobs"
            )
            stages = [_stage_from_job(job) for job in jobs.get("jobs", [])][:6]
        except (httpx.HTTPError, RuntimeError) as exc:
            logger.warning(f"GitHub jobs for {repo}#{run['id']} unavailable: {exc}")

    commit = run.get("head_commit") or {}
    message = (commit.get("message") or run.get("display_title") or "").splitlines()
    branch = run.get("head_branch") or "detached"
    return Pipeline(
        id=f"gh-{run['id']}",
        service=_repo_label(repo),
        branch=f"{branch} \u2190 {run.get('name', 'workflow')}",
        commit_sha=(run.get("head_sha") or "")[:7] or "0000000",
        commit_msg=message[0][:90] if message else "",
        author=(run.get("actor") or {}).get("login") or "unknown",
        status=_status_of(run.get("status"), run.get("conclusion")),
        triggered_at=_relative(run.get("run_started_at") or run.get("created_at")),
        duration_sec=_duration(run.get("run_started_at"), run.get("updated_at")),
        stages=stages,
        url=run.get("html_url"),
        triggered_at_iso=run.get("run_started_at") or run.get("created_at"),
    )


async def _collect() -> PipelineListResponse:
    repos = settings.GITHUB_REPOS
    per_repo = max(1, settings.GITHUB_RUNS_PER_REPO)
    async with httpx.AsyncClient(
        headers=_headers(), timeout=settings.GITHUB_TIMEOUT, follow_redirects=True
    ) as client:
        listings = await asyncio.gather(
            *(
                _fetch_json(
                    client,
                    f"{settings.GITHUB_API_URL}/repos/{repo}/actions/runs",
                    {"per_page": per_repo},
                )
                for repo in repos
            ),
            return_exceptions=True,
        )

        runs: list[tuple[str, dict[str, Any]]] = []
        for repo, listing in zip(repos, listings, strict=False):
            if isinstance(listing, BaseException):
                logger.warning(f"GitHub runs for {repo} unavailable: {listing}")
                continue
            runs.extend((repo, run) for run in listing.get("workflow_runs", [])[:per_repo])

        if not runs:
            raise RuntimeError("no workflow runs available from any configured repository")

        runs.sort(key=lambda item: item[1].get("created_at") or "", reverse=True)
        # Only the newest runs pay for a jobs call, the rest render without stages.
        pipelines = await asyncio.gather(
            *(
                _run_to_pipeline(client, repo, run, with_stages=position < 4)
                for position, (repo, run) in enumerate(runs)
            )
        )

    return PipelineListResponse(
        total=len(pipelines),
        running=sum(1 for p in pipelines if p.status == StageStatus.RUNNING),
        passed=sum(1 for p in pipelines if p.status == StageStatus.PASSED),
        failed=sum(1 for p in pipelines if p.status == StageStatus.FAILED),
        pipelines=list(pipelines),
        source="github",
    )


async def get_github_pipelines(*, force: bool = False) -> PipelineListResponse | None:
    """Cached pipeline list from GitHub, or None when it cannot be fetched.

    Never raises: the caller falls back to the simulated store so the dashboard
    keeps rendering even when GitHub is down or the token is missing.
    """
    if not settings.GITHUB_TOKEN:
        return None

    fresh = time.monotonic() - _cache["at"] < settings.GITHUB_CACHE_TTL
    if _cache["data"] is not None and fresh and not force:
        return _cache["data"]

    try:
        data = await _collect()
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        logger.warning(f"GitHub pipelines unavailable, falling back to the demo store: {exc}")
        return None

    _cache.update(at=time.monotonic(), data=data)
    return data


def reset_cache() -> None:
    """Used by the tests to force a fresh collection."""
    _cache.update(at=0.0, data=None)
