"""Settings parsing tests.

Regression guard: pydantic-settings json.loads() complex fields before validators
run, so a comma separated ALLOWED_ORIGINS used to crash the app at import time.
"""

import json

import pytest

from app.core.config import Settings


def test_allowed_origins_accepts_comma_separated(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.example,https://b.example")
    assert Settings().ALLOWED_ORIGINS == ["https://a.example", "https://b.example"]


def test_allowed_origins_accepts_json(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", json.dumps(["https://a.example"]))
    assert Settings().ALLOWED_ORIGINS == ["https://a.example"]


def test_allowed_origins_single_value(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://only.example")
    assert Settings().ALLOWED_ORIGINS == ["https://only.example"]


@pytest.mark.parametrize("raw", ["true", "false", "1", "0"])
def test_debug_parses_common_booleans(monkeypatch, raw):
    monkeypatch.setenv("DEBUG", raw)
    assert isinstance(Settings().DEBUG, bool)
