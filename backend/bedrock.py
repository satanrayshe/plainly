"""Bedrock Converse wrapper: forced tool call, model fallback chain, hard time budget, usage capture.

Order of attempts for each model:
  1. toolChoice {"tool": {"name": ...}}   (forces the named tool)
  2. toolChoice {"any": {}}               (only if the model rejects the first with a ValidationException)
  3. JSON parsed from plain text           (last resort, via parse_json)
"""
import json
import os
import re
import time

DEFAULT_MODELS = "us.amazon.nova-2-lite-v1:0,us.amazon.nova-pro-v1:0,us.amazon.nova-lite-v1:0"
READ_TIMEOUT_S = 14
MIN_MS_FOR_FALLBACK = 8000
# Slow failures (timeouts, throttling, bad output) count against this; instant ones (access denied, unknown
# model id) just move on to the next model in the chain.
MAX_SLOW_ATTEMPTS = 2

_FAST_FAIL = {"AccessDeniedException", "ResourceNotFoundException", "ValidationException",
              "UnrecognizedClientException", "ModelNotReadyException"}
_client = None


class BedrockUnavailable(Exception):
    """Every model in the chain failed or the time budget ran out."""


class ToolResult:
    def __init__(self, data, model, ms, input_tokens, output_tokens, mode):
        self.data = data
        self.model = model
        self.ms = ms
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.mode = mode  # "tool", "any" or "text"

    def meta(self):
        return {"model": self.model, "ms": self.ms, "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens}


def model_ids():
    return [m.strip() for m in os.environ.get("MODEL_IDS", DEFAULT_MODELS).split(",") if m.strip()]


def client():
    global _client
    if _client is None:
        if os.environ.get("PLAINLY_MOCK") == "1":
            import dev_mock
            _client = dev_mock.FakeBedrockRuntime()
        else:
            import boto3
            from botocore.config import Config
            _client = boto3.client(
                "bedrock-runtime",
                region_name=os.environ.get("AWS_REGION", "us-east-1"),
                # mode=standard makes max_attempts mean total attempts, so botocore never retries by itself;
                # the fallback loop below owns retries and the time budget.
                config=Config(read_timeout=READ_TIMEOUT_S, connect_timeout=3,
                              retries={"max_attempts": 1, "mode": "standard"}),
            )
    return _client


def reset_client():
    global _client
    _client = None


def parse_json(text):
    """Pull a JSON object out of model text, tolerating ``` fences and chatter around it."""
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise


def error_code(exc):
    return getattr(exc, "response", {}).get("Error", {}).get("Code", "") or type(exc).__name__


def call_tool(*, system, messages, tool, max_tokens=1500, remaining_ms=None):
    """Force `tool` and return a ToolResult. remaining_ms: callable giving the milliseconds left in the budget."""
    remaining_ms = remaining_ms or (lambda: 60_000)
    slow_failures = 0
    errors = []
    for index, model in enumerate(model_ids()):
        if index > 0 and remaining_ms() < MIN_MS_FOR_FALLBACK:
            errors.append("skipped fallbacks: time budget")
            break
        try:
            return _call_model(model, system, messages, tool, max_tokens)
        except Exception as exc:  # noqa: BLE001 - classified below, never swallowed silently
            code = error_code(exc)
            errors.append(f"{model}: {code}")
            if code not in _FAST_FAIL:
                slow_failures += 1
                if slow_failures >= MAX_SLOW_ATTEMPTS:
                    break
    raise BedrockUnavailable("; ".join(errors))


def _call_model(model, system, messages, tool, max_tokens):
    request = {
        "modelId": model,
        "system": [{"text": system}],
        "messages": messages,
        "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0},
        "toolConfig": {"tools": [{"toolSpec": tool}], "toolChoice": {"tool": {"name": tool["name"]}}},
    }
    started = time.perf_counter()
    mode = "tool"
    try:
        response = client().converse(**request)
    except Exception as exc:  # noqa: BLE001
        if error_code(exc) != "ValidationException" or "tool" not in str(exc).lower():
            raise
        mode = "any"
        request["toolConfig"]["toolChoice"] = {"any": {}}
        response = client().converse(**request)
    ms = int((time.perf_counter() - started) * 1000)

    content = response.get("output", {}).get("message", {}).get("content", [])
    data = next((block["toolUse"].get("input") for block in content
                 if "toolUse" in block and block["toolUse"].get("name") == tool["name"]), None)
    if data is None:
        mode = "text"
        data = parse_json("".join(block.get("text", "") for block in content))
    if isinstance(data, str):
        data = parse_json(data)
    if not isinstance(data, dict):
        raise ValueError("model returned no tool input")
    usage = response.get("usage", {})
    return ToolResult(data, model, ms, usage.get("inputTokens", 0), usage.get("outputTokens", 0), mode)
