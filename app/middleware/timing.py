import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.logger import logger


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Response-Time"] = f"{elapsed_ms}ms"
        logger.debug(
            f"{request.method} {request.url.path} → "
            f"{response.status_code} [{elapsed_ms}ms]"
        )
        return response
