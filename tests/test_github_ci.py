"""Tests for the GitHub Actions backed pipeline data.

Everything here runs offline: `_fetch_json` is replaced with a fake that serves
recorded shapes of the GitHub API, so the mapping is tested without a token and
without burning rate limit.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services import github_ci

client = TestClient(app)

RUN_SUCCESS = {
    "id": 9001,
    "name": "CI",
    "head_branch": "main",
    "head_sha": "abcdef1234567890",
    "status": "completed",
    "conclusion": "success",
    "created_at": "2026-11-16T19:00:00Z",
    "run_started_at": "2026-11-16T19:00:05Z",
    "updated_at": "2026-11-16T19:01:25Z",
    "html_url": "https://github.com/o/r/actions/runs/9001",
    "actor": {"login": "rintuchowdory"},
    "head_commit": {"message": "ci: run the scan in the docker job\n\nbody"},
    "display_title": "ci: run the scan in the docker job",
}

RUN_FAILED = {
    **RUN_SUCCESS,
    "id": 9002,
    "status": "completed",
    "conclusion": "failure",
    "head_commit": {"message": "ci: broken tag"},
}

RUN_IN_PROGRESS = {
    **RUN_SUCCESS,
    "id": 9003,
    "status": "in_progress",
    "conclusion": None,
    "updated_at": None,
}

RUN_CANCELLED = {**RUN_SUCCESS, "id": 9004, "conclusion": "cancelled"}

JOBS = {
    "jobs": [
        {
            "name": "Lint (ruff)",
            "status": "completed",
            "conclusion": "success",
            "started_at": "2026-11-16T19:00:10Z",
            "completed_at": "2026-11-16T19:00:17Z",
        },
        {
            "name": "Tests (Python 3.12)",
            "status": "completed",
            "conclusion": "failure",
            "started_at": "2026-11-16T19:00:10Z",
            "completed_at": "2026-11-16T19:00:22Z",
        },
        {
            "name": "Build image",
            "status": "in_progress",
            "conclusion": None,
            "started_at": "2026-11-16T19:00:23Z",
            "completed_at": None,
        },
    ]
}


@pytest.fixture
def fake_github(monkeypatch):
    """Serve the fixtures above in place of the real HTTP calls."""

    async def _fetch_json(_client, url, params=None):
        if "/actions/runs/" in url:
            return JOBS
        if params and params.get("per_page"):
            return {"workflow_runs": [RUN_SUCCESS, RUN_FAILED, RUN_IN_PROGRESS]}
        return {"workflow_runs": [RUN_SUCCESS]}

    monkeypatch.setattr(github_ci, "_fetch_json", _fetch_json)
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "ghp_fake")
    monkeypatch.setattr(settings, "GITHUB_REPOS", ["owner/devops-portfolio-microservice"])
    github_ci.reset_cache()
    yield
    github_ci.reset_cache()


# --- mapping -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_token_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "")
    github_ci.reset_cache()
    assert await github_ci.get_github_pipelines(force=True) is None


@pytest.mark.asyncio
async def test_conclusions_map_to_dashboard_statuses(fake_github, monkeypatch):
    monkeypatch.setattr(
        settings,
        "GITHUB_REPOS",
        ["owner/devops-portfolio-microservice"],
    )
    data = await github_ci.get_github_pipelines(force=True)
    assert data is not None
    statuses = {p.id: p.status.value for p in data.pipelines}
    assert statuses["gh-9001"] == "passed"
    assert statuses["gh-9002"] == "failed"
    assert statuses["gh-9003"] == "running"


@pytest.mark.asyncio
async def test_pipeline_fields_are_mapped(fake_github):
    data = await github_ci.get_github_pipelines(force=True)
    passed = next(p for p in data.pipelines if p.id == "gh-9001")
    assert passed.service == "microservice"  # repo prefix stripped
    assert passed.commit_sha == "abcdef1"  # 7 characters, like git log
    assert passed.commit_msg == "ci: run the scan in the docker job"  # first line only
    assert passed.author == "rintuchowdory"
    assert passed.url == "https://github.com/o/r/actions/runs/9001"
    assert passed.triggered_at_iso == "2026-11-16T19:00:05Z"
    assert passed.duration_sec == 80
    assert data.source == "github"


@pytest.mark.asyncio
async def test_stages_come_from_jobs(fake_github):
    data = await github_ci.get_github_pipelines(force=True)
    stages = next(p for p in data.pipelines if p.id == "gh-9001").stages
    assert [s.name for s in stages] == ["Lint (ruff)", "Tests (Python 3.12)", "Build image"]
    assert [s.status.value for s in stages] == ["passed", "failed", "running"]
    assert stages[0].duration_sec == 7
    assert stages[2].duration_sec is not None  # running jobs fall back to "now"


@pytest.mark.asyncio
async def test_counts_match_the_listing(fake_github):
    data = await github_ci.get_github_pipelines(force=True)
    assert data.total == len(data.pipelines) == 3
    assert (data.passed, data.failed, data.running) == (1, 1, 1)


@pytest.mark.asyncio
async def test_cache_serves_the_second_call(fake_github, monkeypatch):
    await github_ci.get_github_pipelines(force=True)
    calls = {"n": 0}
    original = github_ci._collect

    async def counting():
        calls["n"] += 1
        return await original()

    monkeypatch.setattr(github_ci, "_collect", counting)
    await github_ci.get_github_pipelines()
    assert calls["n"] == 0  # served from cache


@pytest.mark.asyncio
async def test_failures_fall_back_to_none(fake_github, monkeypatch):
    async def boom():
        raise RuntimeError("rate limited")

    monkeypatch.setattr(github_ci, "_collect", boom)
    assert await github_ci.get_github_pipelines(force=True) is None


@pytest.mark.asyncio
async def test_partial_repo_failure_still_returns_data(monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "ghp_fake")
    monkeypatch.setattr(
        settings, "GITHUB_REPOS", ["owner/broken", "owner/devops-portfolio-website"]
    )

    async def _fetch_json(_client, url, params=None):
        if "owner/broken" in url:
            raise RuntimeError("404 repo not found")
        if "/actions/runs/" in url:
            return {"jobs": []}
        return {"workflow_runs": [RUN_SUCCESS]}

    monkeypatch.setattr(github_ci, "_fetch_json", _fetch_json)
    github_ci.reset_cache()
    data = await github_ci.get_github_pipelines(force=True)
    github_ci.reset_cache()
    assert data is not None
    assert data.pipelines[0].service == "website"


def test_relative_time_labels():
    assert github_ci._relative(None) == "unknown"
    assert github_ci._relative("not-a-date") == "not-a-date"
    assert github_ci._relative("2020-01-01T00:00:00Z").endswith("d ago")


def test_repo_label_strips_the_shared_prefix():
    assert github_ci._repo_label("rintuchowdory/devops-portfolio-website") == "website"
    assert github_ci._repo_label("rintuchowdory/some-other-repo") == "some-other-repo"


# --- API surface -------------------------------------------------------------


def test_endpoint_reports_its_source(fake_github):
    response = client.get("/api/v1/pipelines")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "github"
    assert body["pipelines"][0]["id"].startswith("gh-")


def test_demo_store_marks_itself_simulated(monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "")
    monkeypatch.setattr(settings, "PIPELINES_SOURCE", "auto")
    github_ci.reset_cache()
    body = client.get("/api/v1/pipelines").json()
    assert body["source"] == "simulated"
    assert body["pipelines"][0]["id"].startswith("pipe-")


def test_trigger_is_refused_for_github_backed_runs(fake_github):
    response = client.post("/api/v1/pipelines/gh-9001/trigger")
    assert response.status_code == 409
    assert "git push" in response.json()["error"]


def test_trigger_still_works_in_demo_mode(monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_TOKEN", "")
    github_ci.reset_cache()
    response = client.post("/api/v1/pipelines/pipe-001/trigger")
    assert response.status_code == 202
    assert response.json()["status"] == "queued"


def test_unknown_pipeline_is_a_json_404(fake_github):
    response = client.get("/api/v1/pipelines/gh-does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"].startswith("Pipeline")
