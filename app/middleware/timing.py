import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core import metrics
from app.core.logger import logger


class TimingMiddleware(BaseHTTPMiddleware):
    """Times every request, adds `X-Response-Time` and feeds the metrics registry."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        metrics.inc_inflight(1)
        try:
            response = await call_next(request)
        finally:
            metrics.inc_inflight(-1)

        elapsed = time.perf_counter() - start
        elapsed_ms = round(elapsed * 1000, 2)

        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"

        # Use the route template ("/api/v1/services/{service_id}") when available so
        # metrics never explode into one series per id.
        route = request.scope.get("route")
        path = getattr(route, "path", None) or request.url.path
        metrics.observe(request.method, path, response.status_code, elapsed)

        logger.debug(
            f"{request.method} {request.url.path} -> " f"{response.status_code} [{elapsed_ms}ms]"
        )
        return response
