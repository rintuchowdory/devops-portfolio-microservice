"""In-process request metrics exposed in Prometheus text exposition format.

Kept dependency free on purpose: a single registry, a thread lock and a
renderer are enough for a container that a Prometheus scraper polls.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict

from app.core.config import settings

_LOCK = threading.Lock()
_STARTED_AT = time.time()

# (method, path template, status code) -> count
_COUNTERS: dict[tuple[str, str, int], int] = defaultdict(int)
# path template -> (sum of seconds, count)
_LATENCY: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
_INFLIGHT = {"value": 0}

_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
_BUCKET_HITS: dict[str, list[int]] = defaultdict(lambda: [0] * len(_BUCKETS))


def observe(method: str, path: str, status_code: int, seconds: float) -> None:
    """Record one finished request."""
    with _LOCK:
        _COUNTERS[(method, path, status_code)] += 1
        _LATENCY[path][0] += seconds
        _LATENCY[path][1] += 1
        hits = _BUCKET_HITS[path]
        for index, upper in enumerate(_BUCKETS):
            if seconds <= upper:
                hits[index] += 1


def inc_inflight(delta: int) -> None:
    with _LOCK:
        _INFLIGHT["value"] = max(0, _INFLIGHT["value"] + delta)


def uptime_seconds() -> float:
    return round(time.time() - _STARTED_AT, 3)


def total_requests() -> int:
    with _LOCK:
        return sum(_COUNTERS.values())


def reset() -> None:
    """Clear the registry. Used by the test suite."""
    with _LOCK:
        _COUNTERS.clear()
        _LATENCY.clear()
        _BUCKET_HITS.clear()
        _INFLIGHT["value"] = 0


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def render_prometheus() -> str:
    """Build the text exposition payload scraped at GET /metrics."""
    with _LOCK:
        counters = dict(_COUNTERS)
        latency = {k: list(v) for k, v in _LATENCY.items()}
        buckets = {k: list(v) for k, v in _BUCKET_HITS.items()}
        inflight = _INFLIGHT["value"]

    lines: list[str] = []

    lines.append("# HELP http_requests_total Total HTTP requests handled, by route and status.")
    lines.append("# TYPE http_requests_total counter")
    for (method, path, status), count in sorted(counters.items()):
        lines.append(
            f'http_requests_total{{method="{_escape(method)}",path="{_escape(path)}",'
            f'status="{status}"}} {count}'
        )

    lines.append("# HELP http_request_duration_seconds Request latency, by route.")
    lines.append("# TYPE http_request_duration_seconds histogram")
    for path in sorted(buckets):
        cumulative = 0
        for index, upper in enumerate(_BUCKETS):
            cumulative = max(cumulative, buckets[path][index])
            lines.append(
                f'http_request_duration_seconds_bucket{{path="{_escape(path)}",'
                f'le="{upper}"}} {cumulative}'
            )
        total = int(latency[path][1]) if path in latency else cumulative
        lines.append(
            f'http_request_duration_seconds_bucket{{path="{_escape(path)}",le="+Inf"}} {total}'
        )
        lines.append(
            f'http_request_duration_seconds_sum{{path="{_escape(path)}"}} '
            f"{round(latency[path][0], 6)}"
        )
        lines.append(f'http_request_duration_seconds_count{{path="{_escape(path)}"}} {total}')

    lines.append("# HELP http_requests_in_flight Requests currently being handled.")
    lines.append("# TYPE http_requests_in_flight gauge")
    lines.append(f"http_requests_in_flight {inflight}")

    lines.append("# HELP process_uptime_seconds Seconds since this process started.")
    lines.append("# TYPE process_uptime_seconds gauge")
    lines.append(f"process_uptime_seconds {uptime_seconds()}")

    lines.append("# HELP app_info Build information for this deployment.")
    lines.append("# TYPE app_info gauge")
    lines.append(
        f'app_info{{service="{_escape(settings.APP_NAME)}",'
        f'version="{_escape(settings.VERSION)}",env="{_escape(settings.ENV)}"}} 1'
    )

    return "\n".join(lines) + "\n"
