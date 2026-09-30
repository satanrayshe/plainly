"""Pipeline with the offline fakes: OCR thresholds, degraded paths, narrate guarantees."""
import base64

import pytest

import bedrock
import dev_mock
import pipeline

SCAM_LETTER = """Internal Revenue Service
Date: September 28, 2026
FINAL NOTICE: you owe $4,812.00.
Pay today with Google Play gift cards or police will arrest you.
Call Officer Smith at 1-888-555-0199."""


def image_payload(text, fmt="image/jpeg"):
    magic = b"\xff\xd8\xff" if fmt == "image/jpeg" else b"\x89PNG"
    data = base64.b64encode(magic + dev_mock.TEXT_MARKER + text.encode()).decode()
    return {"image": {"type": fmt, "data": data}, "today": "2026-09-30"}


class Ctx:
    def __init__(self, ms=28000):
        self.ms = ms

    def get_remaining_time_in_millis(self):
        return self.ms


@pytest.fixture(autouse=True)
def fresh_clients(monkeypatch):
    monkeypatch.delenv("PLAINLY_MOCK_FAIL", raising=False)
    monkeypatch.setattr(pipeline, "_textract", None)
    bedrock.reset_client()
    yield
    bedrock.reset_client()


def test_image_check_end_to_end():
    result = pipeline.run_check(image_payload(SCAM_LETTER), Ctx())
    assert result["verdict"] == "likely_scam"
    assert result["grounding"]["source"] == "textract"
    assert [t["step"] for t in result["trace"][:2]] == ["ocr", "extract"]
    assert result["trace"][0]["detail"] == "Textract read 5 lines"
    assert result["letter_text"].startswith("Internal Revenue Service")
    assert result["meta"]["model"] == "us.amazon.nova-2-lite-v1:0"
    assert set(result) >= {"verdict", "verdict_label", "headline", "agency", "flags", "trace", "extracted",
                           "letter_text", "grounding", "meta"}


def test_pasted_text_skips_ocr():
    result = pipeline.run_check({"text": SCAM_LETTER})
    assert result["trace"][0]["status"] == "skipped"
    assert result["grounding"]["source"] == "pasted_text"


def test_short_ocr_means_not_independently_grounded():
    hindi = "आयकर विभाग\nआपको गिरफ्तार किया जाएगा। तुरंत भुगतान करें।\nRef 12"
    result = pipeline.run_check(image_payload(hindi), Ctx())
    assert result["grounding"]["source"] == "none"
    assert "not independently grounded" in result["trace"][0]["detail"]
    assert all(f["grounded"] is None for f in result["flags"])
    assert result["verdict"] != "consistent_with_genuine"


def test_textract_failure_degrades(monkeypatch):
    monkeypatch.setenv("PLAINLY_MOCK_FAIL", "textract")
    payload = image_payload(SCAM_LETTER)
    payload["text"] = SCAM_LETTER
    result = pipeline.run_check(payload, Ctx())
    assert result["trace"][0]["status"] == "failed"
    assert result["grounding"]["source"] == "pasted_text"
    assert result["verdict"] == "likely_scam"


def test_bedrock_failure_still_runs_rules(monkeypatch):
    monkeypatch.setenv("PLAINLY_MOCK_FAIL", "bedrock")
    result = pipeline.run_check(image_payload(SCAM_LETTER), Ctx())
    assert result["trace"][1] == {"step": "extract", "status": "failed", "ms": 0,
                                  "detail": "The AI reader was unavailable; rules ran on the text alone"}
    assert result["verdict"] == "likely_scam"
    assert result["meta"]["model"] is None


def test_nothing_readable_is_a_pipeline_error(monkeypatch):
    monkeypatch.setenv("PLAINLY_MOCK_FAIL", "both")
    with pytest.raises(pipeline.PipelineError):
        pipeline.run_check(image_payload(SCAM_LETTER), Ctx())


@pytest.mark.parametrize("payload, message", [
    ({}, "Add a photo"),
    ({"image": {"type": "application/pdf", "data": "AAAA"}}, "JPG or PNG"),
    ({"image": {"type": "image/jpeg", "data": "not base64!!"}}, "didn't come through"),
    ({"image": {"type": "image/jpeg", "data": base64.b64encode(b"GIF89a....").decode()}}, "doesn't look like"),
    ({"image": {"type": "image/jpeg", "data": "A" * (pipeline.MAX_IMAGE_B64_CHARS + 4)}}, "too large"),
    ({"text": 42}, "pasted text"),
])
def test_bad_requests(payload, message):
    with pytest.raises(pipeline.BadRequest, match=message):
        pipeline.parse_check_request(payload)


def test_data_url_prefix_and_png_accepted():
    payload = image_payload("hello", "image/png")
    payload["image"]["data"] = "data:image/png;base64," + payload["image"]["data"]
    image, fmt, _text, _today = pipeline.parse_check_request(payload)
    assert fmt == "png" and image.startswith(b"\x89PNG")


def test_client_today_must_be_plausible():
    assert pipeline._client_today("1999-01-01") != pipeline.date(1999, 1, 1)
    assert pipeline._client_today("garbage") == pipeline.date.today()


def test_budget_respects_lambda_time():
    assert pipeline.Budget(Ctx(ms=5000)).remaining_ms() <= 5000 - pipeline.LAMBDA_SAFETY_MS


def _checked(verdict="cant_tell"):
    result = pipeline.run_check({"text": "Internal Revenue Service\nNotice date: September 15, 2026\n"
                                         "Respond within 30 days of the date of this notice. Call 800-829-1040."})
    result["verdict"] = verdict
    return result


def test_narrate_keeps_only_verified_dates(monkeypatch):
    check = _checked()
    fake = {"tldr": "t", "explanation": ["a"], "reply_draft": "Dear IRS",
            "actions": [{"step": "Respond", "how": "by mail", "by": "2026-10-15"},
                        {"step": "Invented", "how": "x", "by": "2026-12-25"}]}
    monkeypatch.setattr(bedrock, "call_tool",
                        lambda **kw: bedrock.ToolResult(fake, "m", 1, 1, 1, "tool"))
    out = pipeline.narrate(check["letter_text"], check, "English", "normal")
    assert [a["by"] for a in out["actions"]] == ["2026-10-15", None]
    assert out["reply_draft"] == "Dear IRS"


def test_narrate_never_drafts_reply_to_a_scam(monkeypatch):
    check = _checked("likely_scam")
    fake = {"tldr": "t", "explanation": [], "actions": [], "reply_draft": "Dear officer, I will pay."}
    monkeypatch.setattr(bedrock, "call_tool", lambda **kw: bedrock.ToolResult(fake, "m", 1, 1, 1, "tool"))
    out = pipeline.narrate("", check, "Hindi", "simple")
    assert out["reply_draft"] == ""
    assert out["actions"][0]["step"] == "Do not pay anything"
    assert out["language"] == "Hindi"


def test_narrate_prompt_gets_verified_brief_not_raw_extraction(monkeypatch):
    seen = {}

    def fake_call(**kw):
        seen.update(kw)
        return bedrock.ToolResult({"tldr": "t", "explanation": [], "actions": [], "reply_draft": ""}, "m", 1, 1, 1,
                                  "tool")

    monkeypatch.setattr(bedrock, "call_tool", fake_call)
    pipeline.narrate("letter", _checked(), "Español", "normal")
    prompt = seen["messages"][0]["content"][0]["text"]
    assert '"computed_from": "letter_date + 30 days"' in prompt
    assert "Español" in seen["system"]
    assert seen["tool"]["name"] == "record_explanation"


def test_narrate_falls_back_when_bedrock_is_down(monkeypatch):
    monkeypatch.setenv("PLAINLY_MOCK_FAIL", "bedrock")
    out = pipeline.narrate("", _checked("likely_scam"), "Hindi", "normal")
    assert out["meta"]["fallback"] is True and out["language"] == "English"
    assert out["reply_draft"] == ""


@pytest.mark.parametrize("language", ["English", "हिन्दी", "Español", "Tamil (India)", "Português do Brasil"])
def test_explain_language_accepted(language):
    assert pipeline.parse_explain_request({"check": {}, "language": language})[2] == language


@pytest.mark.parametrize("language", ["<script>", "x" * 41, "12345", "{{system}}"])
def test_explain_language_rejected(language):
    with pytest.raises(pipeline.BadRequest):
        pipeline.parse_explain_request({"check": {}, "language": language})
