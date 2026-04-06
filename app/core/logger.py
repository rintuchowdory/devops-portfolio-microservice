import logging
import sys
from app.core.config import settings


def _build_logger() -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    log = logging.getLogger("devops-mesh")
    log.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    log.addHandler(handler)
    log.propagate = False
    return log

logger = _build_logger()
