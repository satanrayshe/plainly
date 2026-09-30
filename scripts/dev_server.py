"""Local dev server: static site plus the real Lambda handler for /api/*.

    python scripts/dev_server.py            # offline: Textract and Bedrock are mocked (PLAINLY_MOCK=1)
    python scripts/dev_server.py --live     # real AWS calls with your local credentials
    python scripts/dev_server.py --port 9000 --root site

Serves dist/ if it exists, otherwise site/. "/path" resolves to "/path/index.html", like the CloudFront Function.
Each /api request is turned into a Lambda Function URL (payload v2) event.
"""
import argparse
import mimetypes
import os
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


def make_handler(app, site_root):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(site_root), **kwargs)

        def end_headers(self):
            if not self.path.startswith("/api/"):
                self.send_header("cache-control", "no-cache")
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
    parser.add_argument("--live", action="store_true", help="call real Textract/Bedrock instead of the mocks")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--root", help="directory to serve (default: dist/, else site/)")
    args = parser.parse_args()

    if not args.live:
        os.environ["PLAINLY_MOCK"] = "1"
    os.environ.setdefault("APP_VERSION", "dev-local")
    sys.path.insert(0, str(BACKEND))
    import app  # noqa: E402 - needs the environment above first

    site_root = Path(args.root) if args.root else next(
        (p for p in (ROOT / "dist", ROOT / "site") if p.is_dir()), ROOT)
    server = DevHTTPServer((args.host, args.port), make_handler(app, site_root))
    mode = "LIVE AWS" if args.live else "mocked Textract/Bedrock"
    print(f"Plainly dev server on http://{args.host}:{args.port}  serving {site_root}  ({mode})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
