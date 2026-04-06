from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Ensure these files exist in app/core/
from app.core.config import settings
from app.core.logger import logger
from app.middleware.timing import TimingMiddleware

# Now this import works because we moved the files in Step 1
from app.routers import health, services, pipelines, kubernetes, metrics, logs

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"🚀 DevOps Mesh API starting — {settings.ENV} environment")
    yield
    logger.info("🛑 DevOps Mesh API shutting down")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Production-grade DevOps microservices dashboard API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ──────────────────────────────────────────────────────────────
app.add_middleware(TimingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "ALLOWED_ORIGINS", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ─────────────────────────────────────────────────────────────────
# Note: Ensure each of these files has a 'router = APIRouter()' defined inside!
app.include_router(health.router,     tags=["Health"])
app.include_router(services.router,   prefix="/api/v1", tags=["Services"])
app.include_router(pipelines.router,  prefix="/api/v1", tags=["Pipelines"])
app.include_router(kubernetes.router, prefix="/api/v1", tags=["Kubernetes"])
app.include_router(metrics.router,    prefix="/api/v1", tags=["Metrics"])
app.include_router(logs.router,       prefix="/api/v1", tags=["Logs"])

@app.exception_handler(404)
async def not_found(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Route not found", "path": str(request.url.path)},
    )

@app.exception_handler(500)
async def server_error(request, exc):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )
