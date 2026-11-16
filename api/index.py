"""Vercel serverless entrypoint.

Vercel's Python runtime looks for a module that exposes an ASGI `app`, so this
file only makes the project package importable and re-exports it.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402, F401
