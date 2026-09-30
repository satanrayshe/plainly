"""Plainly API: one Lambda behind CloudFront's /api/* behavior.

Routes
  POST /api/check     {image?: {type, data(base64)}, text?, today?}         -> verdict, flags, trace, ...
  POST /api/explain   {letter_text, check, language, level}                -> plain-language explanation
  GET  /api/health                                                          -> {ok, version}
  GET  /api/stats                                                           -> anonymous counters

Nothing about a letter is stored. Logs are structured JSON with ids, verdicts, rule ids, timings and token
counts only, never letter text.
"""
import base64
import hmac
import ipaddress
import json
import os
import time

import limits
import pipeline

VERSION = os.environ.get("APP_VERSION", "dev")
MAX_BODY_CHARS = 2_500_000
VERDICTS = ("likely_scam", "consistent_with_genuine", "cant_tell")
KNOWN_LANGUAGES = {"english": "english", "hindi": "hindi", "हिन्दी": "hindi", "हिंदी": "hindi",
                   "spanish": "spanish", "español": "spanish", "espanol": "spanish"}

_counters = None


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def counters():
    global _counters
    if _counters is None:
        table_name = os.environ.get("TABLE_NAME")
        if table_name:
            if not os.environ.get("IP_HASH_SALT"):
                # The default salt is public, so hashed IPs in the table could be reversed by brute force.
                print(json.dumps({"level": "warning", "event": "ip_hash_salt_unset"}))
            import boto3
            table = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1")).Table(table_name)
            _counters = limits.DynamoCounters(table)
        else:
            _counters = limits.MemoryCounters()
    return _counters


def set_counters(value):
    """Swap the counter store (tests, dev server)."""
    global _counters
    _counters = value


def respond(status, body, headers=None):
    h = {"content-type": "application/json; charset=utf-8", "cache-control": "no-store",
         "x-content-type-options": "nosniff"}
    h.update(headers or {})
    return {"statusCode": status, "headers": h, "body": json.dumps(body, ensure_ascii=False)}


def log(**fields):
    print(json.dumps({"level": "info", **fields}, default=str))


def client_ip(event):
    """Viewer IP from CloudFront-Viewer-Address ("ip:port", IPv4 or IPv6); else the direct source IP.
    X-Forwarded-For is deliberately ignored: the client controls its first entry."""
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    viewer = (headers.get("cloudfront-viewer-address") or "").strip()
    if viewer:
        return viewer.rsplit(":", 1)[0].strip("[]") if ":" in viewer else viewer
    return event.get("requestContext", {}).get("http", {}).get("sourceIp", "unknown")


def rate_key(ip):
    """What the per-IP limit counts. IPv6 viewers are grouped by /64: one home or server gets a whole /64, so a
    fresh address per request would otherwise dodge the limit."""
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if address.version == 6:
        if address.ipv4_mapped:
            return str(address.ipv4_mapped)
        return f"{ipaddress.ip_network(f'{address}/64', strict=False).network_address}/64"
    return str(address)


def from_cloudfront(event):
    """CloudFront adds x-origin-verify (value in ORIGIN_VERIFY). Without it, anyone could call the API origin
    directly with a forged CloudFront-Viewer-Address and dodge the per-IP limit. Unset locally."""
    expected = os.environ.get("ORIGIN_VERIFY")
    if not expected:
        return True
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    return hmac.compare_digest(headers.get("x-origin-verify", ""), expected)


def enforce_limits(route, event):
    now = time.time()
    per_hour = int(os.environ.get("RATE_LIMIT_PER_HOUR", "20"))
    daily_cap = int(os.environ.get("DAILY_CAP", "400"))
    if route == "explain":
        daily_cap = int(os.environ.get("EXPLAIN_DAILY_CAP", str(daily_cap * 2)))
    window = limits.hour_window(now)
    store = counters()
    if not store.take(f"rl#{route}#{limits.ip_hash(rate_key(client_ip(event)))}#{window}", per_hour,
                      (window + 2) * 3600):
        raise HttpError(429, "You've checked a lot of letters this hour. Please try again a little later, "
                             "or look at the sample letters meanwhile.")
    if not store.take(f"cap#{route}#{limits.utc_day(now)}", daily_cap, now + 2 * 86400):
        raise HttpError(503, "Plainly has reached today's limit of free checks. Please try again tomorrow, "
                             "or look at the sample letters meanwhile.")


def read_json(event):
    body = event.get("body") or ""
    if len(body) > MAX_BODY_CHARS:
        raise HttpError(400, "That photo is too large. Please use a smaller photo (under 1.5 MB).")
    if event.get("isBase64Encoded"):
        try:
            body = base64.b64decode(body).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            raise HttpError(400, "We couldn't read that request. Please try again.") from None
    try:
        payload = json.loads(body or "{}")
    except json.JSONDecodeError:
        raise HttpError(400, "We couldn't read that request. Please try again.") from None
    if not isinstance(payload, dict):
        raise HttpError(400, "We couldn't read that request. Please try again.")
    return payload


def language_bucket(language):
    return KNOWN_LANGUAGES.get((language or "").strip().lower(), "other")


# ---------------------------------------------------------------- routes

def check(event, context, fields):
    request = pipeline.parse_check_request(read_json(event))  # a bad request never uses up the limits
    enforce_limits("check", event)
    result = pipeline.check_request(request, context)
    counters().bump(["checks_total", f"verdict_{result['verdict']}"])
    fields.update(verdict=result["verdict"], rules=[f["rule"] for f in result["flags"]],
                  grounding=result["grounding"]["source"], model=result["meta"]["model"],
                  input_tokens=result["meta"]["input_tokens"], output_tokens=result["meta"]["output_tokens"],
                  steps={t["step"]: t["status"] for t in result["trace"] if not t["step"].startswith("rule:")})
    return respond(200, result)


def explain(event, context, fields):
    payload = read_json(event)
    letter_text, checked, language, level = pipeline.parse_explain_request(payload)
    enforce_limits("explain", event)
    result = pipeline.narrate(letter_text, checked, language, level, pipeline.Budget(context))
    bucket = language_bucket(language)
    counters().bump(["explains_total", f"language_{bucket}"])
    fields.update(language=bucket, verdict=checked.get("verdict"), model=result["meta"]["model"],
                  input_tokens=result["meta"]["input_tokens"], output_tokens=result["meta"]["output_tokens"],
                  fallback=bool(result["meta"].get("fallback")))
    return respond(200, result)


def health(event, context, fields):
    return respond(200, {"ok": True, "version": VERSION})


def stats(event, context, fields):
    values = counters().read()
    return respond(200, {
        "checks_total": values.get("checks_total", 0),
        "by_verdict": {v: values.get(f"verdict_{v}", 0) for v in VERDICTS},
        "explains_total": values.get("explains_total", 0),
        "by_language": {k[len("language_"):]: v for k, v in sorted(values.items()) if k.startswith("language_")},
    })


ROUTES = {
    ("POST", "/api/check"): check,
    ("POST", "/api/explain"): explain,
    ("GET", "/api/health"): health,
    ("GET", "/api/stats"): stats,
}


def handler(event, context):
    started = time.perf_counter()
    http = event.get("requestContext", {}).get("http", {})
    method = http.get("method", "GET").upper()
    path = (event.get("rawPath") or http.get("path") or "/").rstrip("/") or "/"
    fields = {"route": path, "method": method,
              "request_id": getattr(context, "aws_request_id", None)}
    try:
        if not from_cloudfront(event):
            response = respond(403, {"error": "Forbidden."})
        elif method == "OPTIONS":
            response = respond(204, {})
        elif (method, path) in ROUTES:
            response = ROUTES[(method, path)](event, context, fields)
        elif any(p == path for _, p in ROUTES):
            response = respond(405, {"error": "That method isn't supported here."})
        else:
            response = respond(404, {"error": "Not found."})
    except HttpError as e:
        response = respond(e.status, {"error": e.message})
    except pipeline.BadRequest as e:
        response = respond(400, {"error": str(e)})
    except pipeline.PipelineError as e:
        response = respond(502, {"error": str(e)})
    except Exception as e:  # noqa: BLE001 - last line of defence; the type is logged, the letter is not
        fields["error"] = type(e).__name__
        response = respond(502, {"error": "Sorry, something went wrong while reading that. Please try again."})
    fields.update(status=response["statusCode"], ms=int((time.perf_counter() - started) * 1000))
    log(**fields)
    return response
