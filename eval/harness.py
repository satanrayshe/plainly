"""Call the Plainly Lambda handler in-process, the way API Gateway would, for scripts and the eval.

    api = LocalApi(live=False)             # offline: Textract, Bedrock and DynamoDB are faked
    status, body, ms = api.post("/api/check", {"text": "...", "today": "2026-09-30"})

live=True uses real boto3 with whatever AWS credentials the shell has (region us-east-1 by default).
Offline, Bedrock answers come from eval/mock_model.py and Textract returns the text registered for the exact
image bytes with `api.register_ocr(image_bytes, text)`.
"""
import base64
import contextlib
import hashlib
import io
import importlib
import json
import os
import sys
import time
import uuid
from pathlib import Path

import mock_model

ROOT = Path(__file__).resolve().parents[1]
BACKEND = Path(os.environ.get("PLAINLY_BACKEND_DIR") or ROOT / "backend")  # override to test another checkout


class Anything(dict):
    """Permissive stand-in for AWS responses we don't care about offline (counters, metrics, guardrails)."""

    def __missing__(self, key):
        return Anything()

    def __int__(self):
        return 0

    def __float__(self):
        return 0.0

    def __call__(self, *args, **kwargs):
        return Anything()

    def __getattr__(self, name):
        return Anything()


class FakeTextract:
    def __init__(self, ocr_texts):
        self.ocr_texts = ocr_texts

    def detect_document_text(self, Document, **_):
        text = self.ocr_texts.get(hashlib.sha256(Document.get("Bytes", b"")).hexdigest(), "")
        blocks = [{"BlockType": "PAGE", "Id": "page-1"}]
        blocks += [{"BlockType": "LINE", "Id": f"line-{i}", "Text": line, "Confidence": 99.0}
                   for i, line in enumerate(l.strip() for l in text.splitlines() if l.strip())]
        return {"Blocks": blocks, "DocumentMetadata": {"Pages": 1}}

    analyze_document = detect_document_text

    def __getattr__(self, name):
        return Anything()


class FakeBedrock:
    def __init__(self, registry):
        self.registry = registry

    def converse(self, modelId, messages, system=None, toolConfig=None, **_):
        started = time.perf_counter()
        prompt = "\n".join(block.get("text", "") for msg in messages for block in msg.get("content", [])
                           if isinstance(block, dict))
        system_text = "\n".join(block.get("text", "") for block in (system or []))
        tools = [t["toolSpec"] for t in (toolConfig or {}).get("tools", []) if "toolSpec" in t]
        tool = tools[0] if tools else None
        if tool and tool["name"] == "record_letter":
            answer = mock_model.extract(prompt, self.registry)
        else:
            answer = mock_model.narrate(system_text + "\n" + prompt)
        if tool:
            schema = (tool.get("inputSchema") or {}).get("json") or {}
            answer = mock_model.fit_schema(answer, schema)
            content = [{"toolUse": {"toolUseId": "mock-" + uuid.uuid4().hex[:8], "name": tool["name"], "input": answer}}]
            stop = "tool_use"
        else:
            content = [{"text": json.dumps(answer, ensure_ascii=False)}]
            stop = "end_turn"
        tokens_in = (len(prompt) + len(system_text)) // 4
        tokens_out = len(json.dumps(answer)) // 4
        return {
            "output": {"message": {"role": "assistant", "content": content}},
            "stopReason": stop,
            "usage": {"inputTokens": tokens_in, "outputTokens": tokens_out, "totalTokens": tokens_in + tokens_out},
            "metrics": {"latencyMs": int((time.perf_counter() - started) * 1000)},
            "ResponseMetadata": {"RequestId": "mock", "HTTPStatusCode": 200},
        }

    def __getattr__(self, name):
        return Anything()


class FakeContext:
    def __init__(self, budget_ms=29_000):
        self.deadline = time.monotonic() + budget_ms / 1000
        self.aws_request_id = uuid.uuid4().hex
        self.function_name = "plainly-local"

    def get_remaining_time_in_millis(self):
        return max(0, int((self.deadline - time.monotonic()) * 1000))


def _install_fakes(ocr_texts, registry):
    import boto3
    import boto3.session

    def fake_client(service_name, *args, **kwargs):
        if service_name == "textract":
            return FakeTextract(ocr_texts)
        if service_name == "bedrock-runtime":
            return FakeBedrock(registry)
        return Anything()

    def fake_resource(service_name, *args, **kwargs):
        return Anything()

    boto3.client = fake_client
    boto3.resource = fake_resource
    boto3.session.Session.client = lambda self, service_name, *a, **k: fake_client(service_name)
    boto3.session.Session.resource = lambda self, service_name, *a, **k: fake_resource(service_name)
    for key, value in {"AWS_ACCESS_KEY_ID": "offline", "AWS_SECRET_ACCESS_KEY": "offline"}.items():
        os.environ.setdefault(key, value)


class LocalApi:
    def __init__(self, live=False, backend_dir=BACKEND):
        self.live = live
        self.backend_dir = Path(backend_dir)
        self.ocr_texts = {}
        self.last_logs = ""
        os.environ.setdefault("AWS_REGION", "us-east-1")
        os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
        if not live:
            _install_fakes(self.ocr_texts, mock_model.load_registry(self._registry_path()))
        sys.path.insert(0, str(self.backend_dir))
        self.app = importlib.import_module("app")

    def _registry_path(self):
        """The registry the backend will load. Offline, fall back to the test fixture until registry.json lands."""
        if os.environ.get("REGISTRY_PATH"):
            return Path(os.environ["REGISTRY_PATH"])
        real = self.backend_dir / "registry.json"
        fixture = self.backend_dir / "tests" / "fixtures" / "registry_test.json"
        if not real.exists() and fixture.exists():
            print("note: backend/registry.json not found; offline run uses tests/fixtures/registry_test.json",
                  file=sys.stderr)
            os.environ["REGISTRY_PATH"] = str(fixture)
            return fixture
        return real

    @property
    def mode(self):
        return "live" if self.live else "mock"

    def register_ocr(self, image_bytes, text):
        self.ocr_texts[hashlib.sha256(image_bytes).hexdigest()] = text

    def post(self, path, payload, source_ip="198.51.100.7"):
        """Returns (status, parsed JSON body, wall-clock ms)."""
        body = json.dumps(payload, ensure_ascii=False)
        event = {
            "version": "2.0",
            "routeKey": "$default",
            "rawPath": path,
            "rawQueryString": "",
            "headers": {"content-type": "application/json", "user-agent": "plainly-local-harness",
                        "cloudfront-viewer-address": f"{source_ip}:443"},
            "requestContext": {
                "http": {"method": "POST", "path": path, "protocol": "HTTP/1.1", "sourceIp": source_ip,
                         "userAgent": "plainly-local-harness"},
                "requestId": uuid.uuid4().hex,
                "timeEpoch": int(time.time() * 1000),
            },
            "body": body,
            "isBase64Encoded": False,
        }
        logs = io.StringIO()  # the handler prints one JSON log line per request; keep it off the console
        started = time.perf_counter()
        with contextlib.redirect_stdout(logs):
            response = self.app.handler(event, FakeContext())
        ms = int((time.perf_counter() - started) * 1000)
        self.last_logs = logs.getvalue()
        raw = response.get("body") or "{}"
        if response.get("isBase64Encoded"):
            raw = base64.b64decode(raw).decode("utf-8")
        return response.get("statusCode"), json.loads(raw), ms
