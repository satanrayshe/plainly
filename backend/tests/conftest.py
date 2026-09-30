import os
import sys
from datetime import date
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
FIXTURE_REGISTRY = BACKEND / "tests" / "fixtures" / "registry_test.json"

sys.path.insert(0, str(BACKEND))
os.environ["PLAINLY_MOCK"] = "1"
os.environ["REGISTRY_PATH"] = str(FIXTURE_REGISTRY)
os.environ.pop("TABLE_NAME", None)

import agencies  # noqa: E402
import verifier  # noqa: E402

TODAY = date(2026, 9, 30)


@pytest.fixture
def registry():
    return agencies.load_registry(FIXTURE_REGISTRY)


@pytest.fixture
def check(registry):
    """verify() with test defaults; returns the result dict."""

    def run(text, extraction=None, source="pasted_text", today=TODAY):
        return verifier.verify(text, extraction or {}, grounding_source=source, today=today, registry=registry)

    return run


def rules_of(result, severity=None):
    return {f["rule"] for f in result["flags"] if severity is None or f["severity"] == severity}


def flag(result, rule):
    return next(f for f in result["flags"] if f["rule"] == rule)


def trace_step(result, step):
    return next(t for t in result["trace"] if t["step"] == step)
