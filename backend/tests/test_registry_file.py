"""Checks the real backend/registry.json (written by the registry builder) against what the verifier needs."""
from datetime import date
from pathlib import Path

import pytest

import agencies
import contacts
import verifier

REGISTRY = Path(__file__).resolve().parent.parent / "registry.json"
pytestmark = pytest.mark.skipif(not REGISTRY.exists(), reason="backend/registry.json not written yet")


@pytest.fixture(scope="module")
def real():
    return agencies.load_registry(REGISTRY)


def test_schema(real):
    assert set(real["report_channels"]) >= {"US", "IN", "UK"}
    keys = [a["key"] for a in real["agencies"]]
    assert len(keys) == len(set(keys))
    for a in real["agencies"]:
        assert a["country"] in {"US", "IN", "UK"}, a["key"]
        assert a["domains"] or a["phones"], a["key"]
        assert all(d == contacts.host_of(d) for d in a["domains"]), a["key"]
        assert all(p["number"] for p in a["phones"]), a["key"]
        assert a["source_url"].startswith("https://") and date.fromisoformat(a["checked_on"]), a["key"]


def test_no_official_domain_looks_like_another_agency(real):
    domains = agencies.all_domains(real)
    words = agencies.brand_words(real)
    for d in domains:
        assert contacts.lookalike_reason(d, domains, words) is None, d


@pytest.mark.parametrize("text, verdict", [
    ("Internal Revenue Service\nPay today with Google Play gift cards or police will arrest you.", "likely_scam"),
    ("Internal Revenue Service\nNotice date: September 15, 2026\nCall us at 800-829-1040 or visit irs.gov.",
     "consistent_with_genuine"),
    ("This is Officer Sharma from the CBI. A money laundering case is registered against your Aadhaar. "
     "Stay on the video call. Do not tell your family.", "likely_scam"),
    ("UPS: your parcel is waiting. Track it at www.ups.com.", "cant_tell"),
])
def test_scenarios(real, text, verdict):
    result = verifier.verify(text, {}, grounding_source="pasted_text", today=date(2026, 9, 30), registry=real)
    assert result["verdict"] == verdict, [f["rule"] for f in result["flags"]]
