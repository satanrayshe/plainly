"""Serves the built site (dist/, packaged into the zip as site/) when there is no CloudFront in front.

Used when the account can't create CloudFront distributions yet: the HTTP API's $default route sends
every non-/api request here. Same headers CloudFront would add (CSP for Tesseract/pdf.js, security
headers), clean URLs (/try -> /try/index.html), gzip for text when the browser accepts it.
"""
import base64
import gzip
import os
from functools import lru_cache
from pathlib import PurePosixPath

SITE_DIR = os.environ.get("SITE_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")

CSP = ("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self' blob:; "
       "connect-src 'self' data:; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
       "font-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")

SECURITY_HEADERS = {
    "content-security-policy": CSP,
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "permissions-policy": "camera=(self), microphone=(), geolocation=(), payment=(), usb=()",
    "cross-origin-opener-policy": "same-origin",
}

# .traineddata.gz must go out as raw bytes with no Content-Encoding: Tesseract.js gunzips it itself.
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8", ".map": "application/json",
    ".webmanifest": "application/manifest+json", ".xml": "application/xml",
    ".txt": "text/plain; charset=utf-8", ".ics": "text/calendar; charset=utf-8",
    ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".webp": "image/webp", ".gif": "image/gif", ".ico": "image/x-icon",
    ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".otf": "font/otf",
    ".pdf": "application/pdf", ".wasm": "application/wasm",
    ".gz": "application/octet-stream", ".traineddata": "application/octet-stream",
}
COMPRESSIBLE = (".html", ".css", ".js", ".mjs", ".json", ".svg", ".txt", ".xml", ".map", ".webmanifest", ".wasm")
IMMUTABLE_PREFIXES = ("vendor/", "assets/fonts/")
NO_CACHE_SUFFIXES = (".html", ".json", ".webmanifest", ".xml", ".txt", ".ics")
# Lambda responses are capped at 6 MB; base64 adds a third.
MAX_BODY_BYTES = 4_400_000


def enabled():
    return os.environ.get("SERVE_SITE", "").lower() == "true" and os.path.isdir(SITE_DIR)


def resolve(raw_path):
    """URL path -> file relative to SITE_DIR, or None. Refuses anything that escapes the site."""
    parts = [p for p in PurePosixPath("/" + raw_path.lstrip("/")).parts[1:] if p not in ("", ".")]
    if any(p == ".." or p.startswith(".") for p in parts):
        return None
    rel = "/".join(parts)
    candidates = [f"{rel}/index.html" if rel else "index.html"]
    if rel and not raw_path.endswith("/"):
        candidates.insert(0, rel)
    for candidate in candidates:
        full = os.path.join(SITE_DIR, *candidate.split("/"))
        if os.path.isfile(full):
            return candidate
    return None


@lru_cache(maxsize=256)
def _load(rel, compressed):
    with open(os.path.join(SITE_DIR, *rel.split("/")), "rb") as f:
        data = f.read()
    return gzip.compress(data, compresslevel=6, mtime=0) if compressed else data


def _cache_control(rel):
    if rel.startswith(IMMUTABLE_PREFIXES):
        return "public, max-age=31536000, immutable"
    if rel.endswith(NO_CACHE_SUFFIXES):
        return "no-cache"
    return "public, max-age=3600"


def serve(event):
    http = event.get("requestContext", {}).get("http", {})
    method = http.get("method", "GET").upper()
    raw_path = event.get("rawPath") or http.get("path") or "/"
    if method not in ("GET", "HEAD"):
        return _plain(405, "Method not allowed.")
    rel = resolve(raw_path)
    if rel is None:
        rel_404 = resolve("/404.html")
        if rel_404:
            return _file(event, rel_404, status=404, head=method == "HEAD")
        return _plain(404, "Not found.")
    return _file(event, rel, head=method == "HEAD")


def _file(event, rel, status=200, head=False):
    suffix = os.path.splitext(rel)[1].lower()
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    gzip_ok = suffix in COMPRESSIBLE and "gzip" in headers.get("accept-encoding", "")
    body = _load(rel, gzip_ok)
    if len(body) > MAX_BODY_BYTES and not gzip_ok and suffix in COMPRESSIBLE:
        body, gzip_ok = _load(rel, True), True  # too big raw; every current browser accepts gzip
    out = dict(SECURITY_HEADERS)
    out["content-type"] = CONTENT_TYPES.get(suffix, "application/octet-stream")
    out["cache-control"] = _cache_control(rel)
    if gzip_ok:
        out["content-encoding"] = "gzip"
        out["vary"] = "accept-encoding"
    return {"statusCode": status, "headers": out, "isBase64Encoded": True,
            "body": "" if head else base64.b64encode(body).decode("ascii")}


def _plain(status, text):
    out = dict(SECURITY_HEADERS)
    out.update({"content-type": "text/plain; charset=utf-8", "cache-control": "no-store"})
    return {"statusCode": status, "headers": out, "body": text}
