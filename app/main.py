from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logger import logger
from app.middleware.timing import TimingMiddleware
from app.routers import health, kubernetes, logs, metrics, observability, pipelines, services

TAGS_METADATA = [
    {"name": "Health", "description": "Liveness and readiness probes."},
    {"name": "Observability", "description": "Prometheus scrape endpoint and build info."},
    {"name": "Services", "description": "Service catalogue with live-ish runtime stats."},
    {"name": "Pipelines", "description": "CI/CD pipeline runs and manual triggers."},
    {"name": "Kubernetes", "description": "Namespace, pod and capacity overview."},
    {"name": "Metrics", "description": "Dashboard summary and time series per service."},
    {"name": "Logs", "description": "Searchable application logs."},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        f"DevOps Mesh API {settings.VERSION} starting "
        f"(env={settings.ENV}, docs=/docs, metrics=/metrics)"
    )
    yield
    logger.info("DevOps Mesh API shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description=(
        "Production-shaped FastAPI service for the DevOps portfolio: "
        "container image on GHCR, Prometheus metrics, probes and CI that gates every push."
    ),
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# --- Middleware ---------------------------------------------------------------
app.add_middleware(TimingMiddleware)

_origins = settings.ALLOWED_ORIGINS
_allow_all = "*" in _origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _origins,
    allow_credentials=not _allow_all,  # browsers reject credentials with a wildcard origin
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Response-Time"],
)

# --- Routers -----------------------------------------------------------------
app.include_router(health.router, tags=["Health"])
app.include_router(observability.router)
app.include_router(services.router, prefix="/api/v1", tags=["Services"])
app.include_router(pipelines.router, prefix="/api/v1", tags=["Pipelines"])
app.include_router(kubernetes.router, prefix="/api/v1", tags=["Kubernetes"])
app.include_router(metrics.router, prefix="/api/v1", tags=["Metrics"])
app.include_router(logs.router, prefix="/api/v1", tags=["Logs"])


# --- Error handling ----------------------------------------------------------
@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    """Consistent JSON errors that keep the original detail message."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "status_code": 422,
            "path": request.url.path,
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500},
    )
