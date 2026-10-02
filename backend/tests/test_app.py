"""Routing, limits and counters through the Lambda handler, with a fake DynamoDB table."""
import base64
import json
import os
import re
from decimal import Decimal

import pytest

import app
import bedrock
import dev_mock
import limits
import pipeline

SCAM = ("Internal Revenue Service\nPay today with Google Play gift cards or police will arrest you.\n"
        "Call 1-888-555-0199.")


class FakeTable:
    """Implements just the DynamoDB expressions limits.py uses, with boto3's Decimal numbers."""

    def __init__(self):
        self.items = {}

    def update_item(self, Key, UpdateExpression, ExpressionAttributeValues, ConditionExpression=None,
                    ExpressionAttributeNames=None, **_):
        names = ExpressionAttributeNames or {}
        values = {k: Decimal(v) if isinstance(v, int) else v for k, v in ExpressionAttributeValues.items()}
        item = dict(self.items.get(Key["id"], {"id": Key["id"]}))
        if ConditionExpression:
            assert ConditionExpression == "attribute_not_exists(hits) OR hits < :limit"
            if "hits" in item and not item["hits"] < values[":limit"]:
                raise dev_mock.FakeServiceError("ConditionalCheckFailedException", "condition failed")
        add_part, _, set_part = UpdateExpression.partition(" SET ")
        for clause in re.sub(r"^ADD ", "", add_part).split(","):
            name, value = clause.split()
            name = names.get(name, name)
            item[name] = item.get(name, Decimal(0)) + values[value]
        for clause in filter(None, set_part.split(",")):
            name, value = [p.strip() for p in clause.split("=")]
            item[names.get(name, name)] = values[value]
        self.items[Key["id"]] = item

    def get_item(self, Key):
        return {"Item": self.items[Key["id"]]} if Key["id"] in self.items else {}


class Ctx:
    aws_request_id = "req-1"

    def get_remaining_time_in_millis(self):
        return 28000


@pytest.fixture
def table(monkeypatch):
    fake = FakeTable()
    app.set_counters(limits.DynamoCounters(fake))
    monkeypatch.delenv("PLAINLY_MOCK_FAIL", raising=False)
    monkeypatch.setattr(pipeline, "_textract", None)
    bedrock.reset_client()
    yield fake
    app.set_counters(None)


def event(method, path, body=None, ip="203.0.113.7", headers=None):
    h = {"cloudfront-viewer-address": f"{ip}:51234"} if ip else {}
    if os.environ.get("ORIGIN_VERIFY"):
        h["x-origin-verify"] = os.environ["ORIGIN_VERIFY"]
    h.update(headers or {})
    return {"version": "2.0", "rawPath": path, "headers": h,
            "requestContext": {"http": {"method": method, "path": path, "sourceIp": "130.176.0.1"}},
            "body": json.dumps(body) if body is not None else "", "isBase64Encoded": False}


def call(*args, **kwargs):
    response = app.handler(event(*args, **kwargs), Ctx())
    return response["statusCode"], json.loads(response["body"])


def test_health(table, monkeypatch):
    monkeypatch.delenv("AI_MODE", raising=False)
    assert call("GET", "/api/health") == (200, {"ok": True, "version": app.VERSION, "ai_mode": "off"})
    monkeypatch.setenv("AI_MODE", "on")
    assert call("GET", "/api/health")[1]["ai_mode"] == "on"


def test_check_then_explain_and_stats(table):
    status, check = call("POST", "/api/check", {"text": SCAM})
    assert status == 200 and check["verdict"] == "likely_scam"
    letter_text = check.pop("letter_text")
    status, explained = call("POST", "/api/explain",
                             {"letter_text": letter_text, "check": check, "language": "Hindi", "level": "simple"})
    assert status == 200
    assert explained["reply_draft"] == ""
    assert set(explained) >= {"language", "tldr", "explanation", "actions", "jargon", "questions_to_ask",
                              "reply_draft", "meta"}
    status, stats = call("GET", "/api/stats")
    assert stats == {"checks_total": 1, "by_verdict": {"likely_scam": 1, "consistent_with_genuine": 0,
                                                       "cant_tell": 0},
                     "explains_total": 1, "by_language": {"hindi": 1}}


def test_share_route_is_gone(table):
    assert call("POST", "/api/share", {"result": {}})[0] == 404
    assert call("GET", "/api/share")[0] == 404


def test_wrong_method_and_unknown_route(table):
    assert call("GET", "/api/check")[0] == 405
    assert call("GET", "/api/nope") == (404, {"error": "Not found."})
    assert app.handler(event("OPTIONS", "/api/check"), Ctx())["statusCode"] == 204


def test_rate_limit_per_viewer_ip(table, monkeypatch):
    monkeypatch.setenv("ORIGIN_VERIFY", "cdn-secret")  # behind CloudFront: the viewer header is trusted
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "20")
    for _ in range(20):
        assert call("POST", "/api/check", {"text": SCAM}, ip="198.51.100.1")[0] == 200
    status, body = call("POST", "/api/check", {"text": SCAM}, ip="198.51.100.1")
    assert status == 429 and "later" in body["error"]
    # A spoofed X-Forwarded-For does not reset the bucket...
    spoofed = call("POST", "/api/check", {"text": SCAM}, ip="198.51.100.1", headers={"x-forwarded-for": "1.1.1.1"})
    assert spoofed[0] == 429
    # ...but a different viewer is unaffected.
    assert call("POST", "/api/check", {"text": SCAM}, ip="198.51.100.2")[0] == 200


def test_rejected_requests_are_not_counted(table, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "1")
    call("POST", "/api/check", {"text": SCAM}, ip="198.51.100.9")
    call("POST", "/api/check", {"text": SCAM}, ip="198.51.100.9")
    rl = [v for k, v in table.items.items() if k.startswith("rl#check#")]
    assert [int(v["hits"]) for v in rl] == [1]
    assert all("expiresAt" in v for v in rl)


def test_daily_cap_returns_503(table, monkeypatch):
    monkeypatch.setenv("DAILY_CAP", "3")
    for i in range(3):
        assert call("POST", "/api/check", {"text": SCAM}, ip=f"192.0.2.{i}")[0] == 200
    status, body = call("POST", "/api/check", {"text": SCAM}, ip="192.0.2.99")
    assert status == 503 and "sample" in body["error"]


def test_ip_is_hashed_and_counters_have_no_ttl(table):
    call("POST", "/api/check", {"text": SCAM}, ip="203.0.113.50")
    keys = " ".join(table.items)
    assert "203.0.113.50" not in keys
    assert "expiresAt" not in table.items["stats"]


def test_limiter_failure_fails_open(monkeypatch):
    class BrokenTable(FakeTable):
        def update_item(self, **kwargs):
            raise RuntimeError("dynamodb down")

    app.set_counters(limits.DynamoCounters(BrokenTable()))
    try:
        assert call("POST", "/api/check", {"text": SCAM})[0] == 200
    finally:
        app.set_counters(None)


@pytest.mark.parametrize("header, expected", [
    ({"CloudFront-Viewer-Address": "203.0.113.9:443"}, "203.0.113.9"),
    ({"cloudfront-viewer-address": "2001:db8::1:51234"}, "2001:db8::1"),
    ({"x-forwarded-for": "6.6.6.6"}, "130.176.0.1"),
])
def test_client_ip(header, expected, monkeypatch):
    monkeypatch.setenv("ORIGIN_VERIFY", "cdn-secret")
    ev = event("GET", "/api/health", ip=None, headers=header)
    assert app.client_ip(ev) == expected


def test_viewer_header_ignored_without_cloudfront(monkeypatch):
    """No CloudFront in front (ORIGIN_VERIFY unset): a client-sent CloudFront-Viewer-Address must not move the key."""
    monkeypatch.delenv("ORIGIN_VERIFY", raising=False)
    ev = event("GET", "/api/health", ip="9.9.9.9")
    assert app.client_ip(ev) == "130.176.0.1"


def test_payload_size_limit(table, monkeypatch):
    big = {"image": {"type": "image/jpeg", "data": "A" * 2_200_004}}
    status, body = call("POST", "/api/check", big)
    assert status == 400 and "on your device" in body["error"]  # AI_MODE=off takes no images at all
    status, body = call("POST", "/api/check", {"text": "x" * 30_001})
    assert status == 400 and "30,000" in body["error"]
    monkeypatch.setenv("AI_MODE", "on")
    status, body = call("POST", "/api/check", big)
    assert status == 400 and "too large" in body["error"]
    huge = event("POST", "/api/check")
    huge["body"] = "x" * (app.MAX_BODY_CHARS + 1)
    assert app.handler(huge, Ctx())["statusCode"] == 400


def test_bad_json_and_base64_body(table):
    ev = event("POST", "/api/check")
    ev["body"] = "{not json"
    assert app.handler(ev, Ctx())["statusCode"] == 400
    ev = event("POST", "/api/check")
    ev["body"] = base64.b64encode(json.dumps({"text": SCAM}).encode()).decode()
    ev["isBase64Encoded"] = True
    assert app.handler(ev, Ctx())["statusCode"] == 200


def test_explain_requires_check(table):
    status, body = call("POST", "/api/explain", {"letter_text": "x", "language": "English"})
    assert status == 400 and "check the letter first" in body["error"]


def test_unreadable_letter_is_502(table, monkeypatch):
    monkeypatch.setenv("AI_MODE", "on")
    monkeypatch.setenv("PLAINLY_MOCK_FAIL", "both")
    payload = {"image": {"type": "image/jpeg", "data": base64.b64encode(b"\xff\xd8\xff" + b"x").decode()}}
    status, body = call("POST", "/api/check", payload)
    assert status == 502 and "couldn't read" in body["error"]


def test_unexpected_error_is_friendly_and_logged_by_type(table, monkeypatch, capsys):
    def boom(*a, **k):
        raise KeyError("secret letter words")

    monkeypatch.setattr(pipeline, "check_request", boom)
    status, body = call("POST", "/api/check", {"text": SCAM})
    assert status == 502 and "went wrong" in body["error"]
    out = capsys.readouterr().out
    assert '"error": "KeyError"' in out and "secret letter words" not in out


def test_logs_are_structured_and_never_contain_letter_text(table, capsys):
    call("POST", "/api/check", {"text": SCAM})
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")]
    entry = next(line for line in lines if line.get("route") == "/api/check")
    assert entry["status"] == 200 and entry["verdict"] == "likely_scam"
    assert "payment_gift_card" in entry["rules"]
    dumped = json.dumps(lines)
    assert "Google Play" not in dumped and "888-555-0199" not in dumped and "203.0.113.7" not in dumped


def test_response_headers(table):
    response = app.handler(event("GET", "/api/health"), Ctx())
    assert response["headers"]["cache-control"] == "no-store"
    assert response["headers"]["content-type"].startswith("application/json")


def test_origin_verify_header_required_when_configured(table, monkeypatch):
    monkeypatch.setenv("ORIGIN_VERIFY", "stack-uuid")
    assert call("GET", "/api/health", headers={"x-origin-verify": ""})[0] == 403  # helper adds it by default
    assert call("GET", "/api/health", headers={"x-origin-verify": "wrong"})[0] == 403
    assert call("GET", "/api/health", headers={"X-Origin-Verify": "stack-uuid"})[0] == 200


@pytest.mark.parametrize("ip, key", [
    ("203.0.113.9", "203.0.113.9"),
    ("2001:db8:1:2:aaaa::1", "2001:db8:1:2::/64"),
    ("2001:db8:1:2:ffff:ffff:ffff:ffff", "2001:db8:1:2::/64"),
    ("::ffff:198.51.100.4", "198.51.100.4"),
    ("unknown", "unknown"),
])
def test_rate_key_groups_ipv6_by_prefix(ip, key):
    assert app.rate_key(ip) == key


def test_new_ipv6_address_per_request_shares_one_bucket(table, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "2")
    for suffix in ("1", "2"):
        assert call("POST", "/api/check", {"text": SCAM}, ip=f"[2001:db8:5:6::{suffix}]")[0] == 200
    assert call("POST", "/api/check", {"text": SCAM}, ip="[2001:db8:5:6::3]")[0] == 429


def test_bad_requests_do_not_use_up_the_limits(table, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "1")
    monkeypatch.setenv("DAILY_CAP", "1")
    for bad in ({}, {"image": {"type": "image/gif", "data": "R0lG"}}, {"image": {"type": "image/jpeg", "data": "%%"}}):
        assert call("POST", "/api/check", bad, ip="198.51.100.20")[0] == 400
    assert call("POST", "/api/check", {"text": SCAM}, ip="198.51.100.20")[0] == 200


def test_oversized_explain_check_is_rejected(table):
    check = {"verdict": "cant_tell", "flags": [{"title": "x" * 150_000}]}
    status, body = call("POST", "/api/explain", {"letter_text": "hi", "check": check, "language": "English"})
    assert status == 400 and "too large" in body["error"]


def test_explain_has_a_higher_hourly_limit_with_ai_off(table, monkeypatch):
    monkeypatch.delenv("AI_MODE", raising=False)
    monkeypatch.delenv("EXPLAIN_RATE_LIMIT_PER_HOUR", raising=False)
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "2")
    status, check = call("POST", "/api/check", {"text": SCAM}, ip="198.51.100.30")
    letter_text = check.pop("letter_text")
    body = {"letter_text": letter_text, "check": check, "language": "English"}
    # 7 letters in 3 languages is 21 explanations: more than the check limit, within the explain one.
    for _ in range(2 * app.EXPLAIN_RATE_FACTOR_OFF):
        assert call("POST", "/api/explain", body, ip="198.51.100.30")[0] == 200
    assert call("POST", "/api/explain", body, ip="198.51.100.30")[0] == 429
    assert app.per_hour_limit("check") == 2
    monkeypatch.setenv("EXPLAIN_RATE_LIMIT_PER_HOUR", "7")
    assert app.per_hour_limit("explain") == 7
    monkeypatch.delenv("EXPLAIN_RATE_LIMIT_PER_HOUR")
    monkeypatch.setenv("AI_MODE", "on")
    assert app.per_hour_limit("explain") == 2  # each explanation is a model call then


def test_a_check_that_was_accepted_can_be_explained(table):
    head = "Pay by 2027-01-15 at irs-gov-pay.com urgent today gift card OTP\n"
    text = "Internal Revenue Service\n" + "".join(
        f"Pay by 2027-{1 + i % 12:02d}-{1 + i % 28:02d} at irs-gov{i}.com urgent today gift card OTP\n"
        for i in range(500))
    text = text[:29_900]
    status, check = call("POST", "/api/check", {"text": text}, ip="198.51.100.31")
    assert status == 200
    letter_text = check.pop("letter_text")
    assert len(json.dumps(check, ensure_ascii=False)) > pipeline.MAX_CHECK_CHARS  # the old limit refused this
    status, explained = call("POST", "/api/explain", {"letter_text": letter_text, "check": check,
                                                      "language": "Spanish", "today": "2026-10-01"},
                             ip="198.51.100.31")
    assert status == 200 and explained["tldr"]
