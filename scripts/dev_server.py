"""Local dev server: static site plus the real Lambda handler for /api/*.

    python scripts/dev_server.py            # production path (AI_MODE=off): text only, rules reader, templates;
                                            #   makes no AWS calls at all
    python scripts/dev_server.py --ai-mock  # AI_MODE=on with Textract and Bedrock mocked (PLAINLY_MOCK=1)
    python scripts/dev_server.py --live     # AI_MODE=on with real AWS calls (needs Bedrock/Textract access)
    python scripts/dev_server.py --port 9000 --root site
    python scripts/dev_server.py --csp      # also send the CloudFront response headers from infra/template.yaml
                                            #   (Content-Security-Policy, nosniff, ...) to test the site under them

Serves dist/ if it exists, otherwise site/. "/path" resolves to "/path/index.html", like the CloudFront Function.
Each /api request is turned into a Lambda Function URL (payload v2) event.
"""
import argparse
import mimetypes
import os
import re
import sys
import time
import uuid
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
LAMBDA_TIMEOUT_MS = 29000

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("application/manifest+json", ".webmanifest")
# Same as deploy.sh: Tesseract language data is gzip bytes served as-is, never with Content-Encoding.
SimpleHTTPRequestHandler.extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                                           ".gz": "application/octet-stream", ".wasm": "application/wasm"}


def template_headers(path=ROOT / "infra" / "template.yaml"):
    """The response headers the CloudFront ResponseHeadersPolicy in template.yaml sends, read from the template so
    a local test can't drift from what is deployed."""
    text = path.read_text(encoding="utf-8")
    csp = re.search(r"ContentSecurityPolicy: >-\r?\n((?:[ ]{14,}.*\r?\n)+)", text)
    if not csp:
        raise SystemExit("Could not find the Content-Security-Policy in infra/template.yaml")
    headers = {"Content-Security-Policy": " ".join(line.strip() for line in csp.group(1).splitlines()),
               "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
               "Referrer-Policy": "strict-origin-when-cross-origin", "X-XSS-Protection": "0"}
    for name, value in re.findall(r"- Header: ([\w-]+)\r?\n\s+Value: (.+)", text):
        headers[name] = value.strip()
    return headers


class DevHTTPServer(ThreadingHTTPServer):
    # On Windows SO_REUSEADDR lets a second server bind a port that is already in use, and requests then go to
    # whichever process Windows picks. Fail loudly instead.
    allow_reuse_address = sys.platform != "win32"


class FakeContext:
    def __init__(self):
        self.aws_request_id = str(uuid.uuid4())
        self.deadline = time.monotonic() + LAMBDA_TIMEOUT_MS / 1000

    def get_remaining_time_in_millis(self):
        return max(0, int((self.deadline - time.monotonic()) * 1000))


def make_handler(app, site_root, extra_headers=None):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(site_root), **kwargs)

        def end_headers(self):
            if not self.path.startswith("/api/"):
                self.send_header("cache-control", "no-cache")
            for name, value in (extra_headers or {}).items():
                self.send_header(name, value)
            super().end_headers()

        def translate_path(self, path):
            fs_path = Path(super().translate_path(path))
            if fs_path.is_dir():
                return str(fs_path / "index.html")
            if not fs_path.exists() and not fs_path.suffix:
                return str(fs_path) + "/index.html"
            return str(fs_path)

        def do_GET(self):
            if self.path.startswith("/api/"):
                return self.lambda_call("GET")
            return super().do_GET()

        def do_POST(self):
            if self.path.startswith("/api/"):
                return self.lambda_call("POST")
            self.send_error(405)

        def do_OPTIONS(self):
            return self.lambda_call("OPTIONS")

        def lambda_call(self, method):
            path, _, query = self.path.partition("?")
            length = int(self.headers.get("content-length") or 0)
            body = self.rfile.read(length).decode("utf-8", errors="replace") if length else ""
            port = self.client_address[1]
            headers = {k.lower(): v for k, v in self.headers.items()}
            headers.setdefault("cloudfront-viewer-address", f"{self.client_address[0]}:{port}")
            event = {
                "version": "2.0",
                "rawPath": path,
                "rawQueryString": query,
                "headers": headers,
                "requestContext": {"http": {"method": method, "path": path, "sourceIp": self.client_address[0]}},
                "body": body,
                "isBase64Encoded": False,
            }
            result = app.handler(event, FakeContext())
            payload = (result.get("body") or "").encode("utf-8")
            self.send_response(result["statusCode"])
            for name, value in (result.get("headers") or {}).items():
                self.send_header(name, value)
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt, *args):
            sys.stderr.write(f"[dev] {self.address_string()} {fmt % args}\n")

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--ai-mock", action="store_true", help="AI_MODE=on with mocked Textract/Bedrock")
    mode.add_argument("--live", action="store_true", help="AI_MODE=on with real Textract/Bedrock")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--root", help="directory to serve (default: dist/, else site/)")
    parser.add_argument("--csp", action="store_true",
                        help="send the CloudFront response headers (CSP etc.) from infra/template.yaml")
    args = parser.parse_args()

    os.environ["AI_MODE"] = "on" if args.live or args.ai_mock else "off"
    if args.ai_mock:
        os.environ["PLAINLY_MOCK"] = "1"
    os.environ.setdefault("APP_VERSION", "dev-local")
    sys.path.insert(0, str(BACKEND))
    import app  # noqa: E402 - needs the environment above first

    site_root = Path(args.root) if args.root else next(
        (p for p in (ROOT / "dist", ROOT / "site") if p.is_dir()), ROOT)
    extra = template_headers() if args.csp else None
    server = DevHTTPServer((args.host, args.port), make_handler(app, site_root, extra))
    mode = ("AI_MODE=on, LIVE AWS" if args.live else "AI_MODE=on, mocked Textract/Bedrock" if args.ai_mock
            else "AI_MODE=off: rules reader + templates, no AWS")
    print(f"Plainly dev server on http://{args.host}:{args.port}  serving {site_root}  ({mode})", flush=True)
    if extra:
        print(f"Sending template.yaml response headers; CSP: {extra['Content-Security-Policy']}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
