"""Converse wrapper: tool forcing, toolChoice downgrade, JSON-in-text fallback, model chain and time budget."""
import json

import pytest

import bedrock
from dev_mock import FakeServiceError

TOOL = {"name": "record_letter", "description": "d", "inputSchema": {"json": {"type": "object"}}}


def tool_response(data, name="record_letter"):
    return {"output": {"message": {"content": [{"toolUse": {"toolUseId": "1", "name": name, "input": data}}]}},
            "usage": {"inputTokens": 100, "outputTokens": 20}}


def text_response(text):
    return {"output": {"message": {"content": [{"text": text}]}}, "usage": {"inputTokens": 50, "outputTokens": 10}}


class ScriptedClient:
    """Plays back one scripted outcome per converse() call and records the requests."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def converse(self, **request):
        self.requests.append(json.loads(json.dumps(request)))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


@pytest.fixture
def use_client(monkeypatch):
    monkeypatch.setenv("MODEL_IDS", "model-a,model-b,model-c")

    def install(client):
        monkeypatch.setattr(bedrock, "_client", client)
        return client

    yield install
    bedrock.reset_client()


def call(**kwargs):
    return bedrock.call_tool(system="s", messages=[{"role": "user", "content": [{"text": "hi"}]}], tool=TOOL,
                             **kwargs)


def test_forced_tool_call(use_client):
    client = use_client(ScriptedClient(tool_response({"claimed_sender": "IRS"})))
    result = call()
    assert result.data == {"claimed_sender": "IRS"}
    assert result.mode == "tool" and result.model == "model-a"
    assert result.meta()["input_tokens"] == 100 and result.meta()["output_tokens"] == 20
    request = client.requests[0]
    assert request["toolConfig"]["toolChoice"] == {"tool": {"name": "record_letter"}}
    assert request["inferenceConfig"] == {"maxTokens": 1500, "temperature": 0}


def test_tool_choice_rejected_retries_with_any(use_client):
    client = use_client(ScriptedClient(
        FakeServiceError("ValidationException", "This model doesn't support the toolChoice.tool field"),
        tool_response({"ok": 1})))
    result = call()
    assert result.mode == "any" and result.model == "model-a"
    assert client.requests[1]["toolConfig"]["toolChoice"] == {"any": {}}


def test_json_in_text_last_resort(use_client):
    use_client(ScriptedClient(text_response('Here you go:\n```json\n{"claimed_sender": "SSA"}\n```')))
    result = call()
    assert result.mode == "text" and result.data == {"claimed_sender": "SSA"}


def test_access_denied_moves_to_next_model(use_client):
    use_client(ScriptedClient(FakeServiceError("AccessDeniedException", "no access"), tool_response({"ok": 1})))
    assert call().model == "model-b"


def test_at_most_one_retry_after_slow_failures(use_client):
    client = use_client(ScriptedClient(FakeServiceError("ThrottlingException", "slow down"),
                                       FakeServiceError("ModelTimeoutException", "timeout"),
                                       tool_response({"never": "reached"})))
    with pytest.raises(bedrock.BedrockUnavailable):
        call()
    assert [r["modelId"] for r in client.requests] == ["model-a", "model-b"]


def test_unparseable_output_counts_as_failure(use_client):
    use_client(ScriptedClient(text_response("I cannot help with that."), tool_response({"ok": 1})))
    result = call()
    assert result.model == "model-b"


def test_fallbacks_skipped_when_budget_low(use_client):
    client = use_client(ScriptedClient(FakeServiceError("ThrottlingException", "slow down"), tool_response({})))
    with pytest.raises(bedrock.BedrockUnavailable, match="time budget"):
        call(remaining_ms=lambda: 7000)
    assert len(client.requests) == 1


def test_first_call_not_started_without_time_for_it(use_client):
    client = use_client(ScriptedClient(tool_response({})))
    with pytest.raises(bedrock.BedrockUnavailable, match="time budget"):
        call(remaining_ms=lambda: bedrock.MIN_MS_FOR_CALL - 1)
    assert client.requests == []


def test_tool_choice_retry_not_started_without_time_for_it(use_client):
    left = iter([20000, 20000, 4000, 4000])
    client = use_client(ScriptedClient(
        FakeServiceError("ValidationException", "This model doesn't support the toolChoice.tool field"),
        tool_response({"ok": 1})))
    with pytest.raises(bedrock.BedrockUnavailable):
        call(remaining_ms=lambda: next(left))
    assert len(client.requests) == 1


@pytest.mark.parametrize("remaining_ms, seconds", [(60000, 14), (23000, 14), (9000, 4), (6000, 1), (0, 1)])
def test_read_timeout_leaves_headroom(remaining_ms, seconds):
    timeout = bedrock.read_timeout_for(remaining_ms)
    assert timeout == seconds
    if remaining_ms >= bedrock.MIN_MS_FOR_CALL:
        assert (timeout + bedrock.CONNECT_TIMEOUT_S) * 1000 + bedrock.HEADROOM_MS <= remaining_ms


def test_clients_are_cached_per_timeout(monkeypatch):
    pytest.importorskip("boto3")
    monkeypatch.delenv("PLAINLY_MOCK", raising=False)
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    bedrock.reset_client()
    try:
        slow, quick = bedrock.client(14), bedrock.client(4)
        assert slow is bedrock.client(14) and slow is not quick
        assert quick.meta.config.read_timeout == 4 and slow.meta.config.read_timeout == 14
    finally:
        bedrock.reset_client()


def test_default_model_chain(monkeypatch):
    monkeypatch.delenv("MODEL_IDS", raising=False)
    assert bedrock.model_ids() == ["us.amazon.nova-2-lite-v1:0", "us.amazon.nova-pro-v1:0",
                                   "us.amazon.nova-lite-v1:0"]


def test_parse_json_variants():
    assert bedrock.parse_json('{"a": 1}') == {"a": 1}
    assert bedrock.parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert bedrock.parse_json('Sure! {"a": {"b": 2}} Hope that helps.') == {"a": {"b": 2}}
    with pytest.raises(ValueError):
        bedrock.parse_json("no json at all")
