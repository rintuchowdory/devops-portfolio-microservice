# devops-portfolio-microservice

[![CI](https://github.com/rintuchowdory/devops-portfolio-microservice/actions/workflows/ci.yml/badge.svg)](https://github.com/rintuchowdory/devops-portfolio-microservice/actions/workflows/ci.yml)
[![Live API](https://img.shields.io/badge/live-api-2ea44f)](https://devops-portfolio-microservice.vercel.app/health)
[![Swagger](https://img.shields.io/badge/docs-swagger-85EA2D)](https://devops-portfolio-microservice.vercel.app/docs)
[![Image](https://img.shields.io/badge/ghcr.io-devops--portfolio--microservice-2496ED)](https://github.com/rintuchowdory/devops-portfolio-microservice/pkgs/container/devops-portfolio-microservice)

A FastAPI service that models the data a DevOps dashboard needs: services, CI/CD
pipelines, Kubernetes namespaces, metrics and logs. It exists to show the whole
delivery path in one repository, from tests to a signed container image.

- Live API: <https://devops-portfolio-microservice.vercel.app>
- Interactive docs: <https://devops-portfolio-microservice.vercel.app/docs>
- Prometheus metrics: <https://devops-portfolio-microservice.vercel.app/metrics>

Most routes serve deterministic demo telemetry held in memory
(`app/services/store.py`), clearly marked as such. One route does not:
`/api/v1/pipelines` reads the **real** workflow runs of this repository and the
website repository from the GitHub Actions API, so the dashboard reports on the
pipeline that actually ships the project. The response carries `source`:
`github` or `simulated`.

```bash
curl -s https://devops-portfolio-microservice.vercel.app/api/v1/pipelines | jq '.source, .pipelines[0]'
```

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | Service index with links to docs and probes |
| GET | `/health` | Liveness probe, returns version, env and uptime |
| GET | `/health/ready` | Readiness probe, verifies the data layer answers |
| GET | `/metrics` | Prometheus text exposition (counters, latency histogram, uptime, build info) |
| GET | `/metrics/json` | Same counters as JSON for dashboards |
| GET | `/api/v1/services` | Service catalogue, filter by `status`, `namespace`, `tag` |
| GET | `/api/v1/services/{id}` | Single service |
| GET | `/api/v1/pipelines` | Real GitHub Actions runs (`source: github`), filter by `status`, `service` |
| GET | `/api/v1/pipelines/{id}` | Single pipeline with its stages |
| POST | `/api/v1/pipelines/{id}/trigger` | Queues a run in demo mode, returns `202`; `409` for real GitHub runs |
| GET | `/api/v1/kubernetes` | Namespace, pod and capacity overview |
| GET | `/api/v1/kubernetes/{id}` | Single namespace |
| GET | `/api/v1/metrics/summary` | Dashboard headline numbers |
| GET | `/api/v1/metrics/services/{id}` | Time series for one service |
| GET | `/api/v1/logs` | Log search, filter by `service`, `level`, `limit` |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |

Every response carries `X-Response-Time`. Errors are always JSON and keep their
detail message:

```json
{ "error": "Service 'nope' not found", "status_code": 404, "path": "/api/v1/services/nope" }
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload
```

Then open <http://127.0.0.1:8000/docs>.

### Tests and lint

```bash
pytest -q                 # 45 tests
ruff check .              # lint
ruff format --check .     # formatting
```

The suite covers every route, the 404 and 422 payload shape, CORS preflight, the
Prometheus exposition format, the route-template metric labels, and regressions for
two bugs that used to break production: a `ValueError` in the time-series builder
whenever the UTC minute was smaller than the series length, and a settings crash on
a comma separated `ALLOWED_ORIGINS`.

## Docker

```bash
docker build -t devops-mesh .
docker run --rm -p 8000:8000 devops-mesh
curl -s localhost:8000/health
```

The final image runs as the unprivileged user `appuser`, installs only runtime
dependencies and ships a `HEALTHCHECK` against `/health`. `docker build --target test .`
runs the test suite inside the image.

## Configuration

| Variable | Default | Notes |
| --- | --- | --- |
| `ENV` | `development` | Reported by `/health` and in `app_info` |
| `DEBUG` | `true` | |
| `PORT` | `8000` | Uvicorn bind port in the container |
| `LOG_LEVEL` | `INFO` | |
| `ALLOWED_ORIGINS` | localhost + the Pages origin | Comma separated or a JSON array |
| `METRICS_TTL` | `5` | Refresh interval used by the summary payload |
| `GITHUB_TOKEN` | empty | Read-only token for the Actions API. Without it `/api/v1/pipelines` falls back to demo data |
| `GITHUB_REPOS` | both portfolio repos | Comma separated `owner/repo` list to read workflow runs from |
| `GITHUB_RUNS_PER_REPO` | `3` | How many recent runs each repository contributes |
| `GITHUB_CACHE_TTL` | `60` | Seconds a collected result is reused, keeps the API well inside the rate limit |
| `GITHUB_TIMEOUT` | `8` | Per-request timeout towards `api.github.com` |
| `PIPELINES_SOURCE` | `auto` | `auto`, `github` or `simulated` |

Copy `.env.example` to `.env` for local use. `.env` is git-ignored.

### Real CI data

`app/services/github_ci.py` collects the latest workflow runs per configured
repository, maps conclusions onto the dashboard vocabulary
(`success` -> `passed`, `failure` -> `failed`, `in_progress` -> `running`), and
pulls the job list of the newest runs so each pipeline can show its stages.

Design choices worth noting:

- **Cached, not proxied.** A 60 second TTL means a busy dashboard costs GitHub one
  request per minute, not one per browser refresh.
- **Degrades instead of failing.** No token, a rate limit or a broken repository
  returns the demo store and logs a warning. The site never renders an empty panel.
- **Honest triggers.** Runs read from GitHub cannot be queued through this API, so
  `POST /pipelines/{id}/trigger` answers `409` with the command that does work
  (`git push`, `gh workflow run`) instead of pretending to queue one.

## CI/CD

`.github/workflows/ci.yml` runs on every push and pull request:

1. **lint**: `ruff check` and `ruff format --check`
2. **test**: `pytest` on Python 3.11, 3.12 and 3.13
3. **docker**: Buildx build with GitHub Actions layer caching, then a smoke test that
   boots the container and polls `/health` before touching `/metrics`
4. On `main` and `v*.*.*` tags the image is pushed to
   `ghcr.io/rintuchowdory/devops-portfolio-microservice` with `latest`, branch, `sha-`
   and semver tags, plus build provenance and an SBOM
5. **scan**: Trivy reports critical and high findings for the pushed image

Pull requests validate the Docker build but never push.

```bash
docker pull ghcr.io/rintuchowdory/devops-portfolio-microservice:latest
```

## Deployment

`render.yaml` describes a Render web service with the health check wired to `/health`.

The live instance currently runs on Vercel's Python runtime through `api/index.py`,
which re-exports the ASGI app, because that keeps a public demo online without a
card on file. The container image is the portable artifact; the Vercel entrypoint is
only a hosting adapter.

```bash
vercel deploy --prod
```

## Layout

```
app/
  main.py                 app factory, middleware, routers, error handlers
  core/config.py          settings (env or .env)
  core/metrics.py         request counters and Prometheus renderer
  core/logger.py          stdout logger
  middleware/timing.py    X-Response-Time and metric recording
  models/schemas.py       pydantic contracts
  routers/                health, observability, services, pipelines, kubernetes, metrics, logs
  services/store.py       in-memory demo data
api/index.py              Vercel serverless entrypoint
tests/                    pytest suite
```
