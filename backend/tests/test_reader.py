"""reader.py is the keyword reader the frozen offline eval measured, moved to the backend unchanged.

Proof, on every eval text (dev, synthetic, holdout) and every sample letter text:
  1. reader.extract() == eval/mock_model.extract() (the old code, still in eval/ for the AI_MODE=on fakes),
  2. reader.extract() hashes to what the old reader produced on 2026-10-01 (fixtures/reader_golden.json), so the
     proof still holds if eval/mock_model.py is later reduced to a re-export of reader.py,
  3. the whole /api/check result with AI_MODE=off equals the AI_MODE=on result when the fake model answers with
     the old reader (only the trace wording and meta differ).
The holdout texts are only read here to compare two copies of the same reader; no rule is tuned on them.
"""
import hashlib
import json
import sys

import pytest

from conftest import BACKEND, TODAY

import agencies  # noqa: E402
import bedrock  # noqa: E402
import pipeline  # noqa: E402
import reader  # noqa: E402

ROOT = BACKEND.parent
sys.path.insert(0, str(ROOT / "eval"))
import mock_model  # noqa: E402

REGISTRY_FILE = BACKEND / "registry.json"
GOLDEN = json.loads((BACKEND / "tests" / "fixtures" / "reader_golden.json").read_text(encoding="utf-8"))


def all_texts():
    out = {}
    for name in ("dev", "holdout"):
        for path in sorted((ROOT / "eval" / name).glob("*.json")):
            out[f"{name}/{path.stem}"] = json.loads(path.read_text(encoding="utf-8"))["text"]
    for case in json.loads((ROOT / "eval" / "synthetic" / "letters.json").read_text(encoding="utf-8")):
        out[f"synthetic/{case['id']}"] = case["text"]
    for path in sorted((ROOT / "samples" / "letters").glob("*.txt")):
        out[f"samples/{path.stem}"] = path.read_text(encoding="utf-8").strip()
    return out


TEXTS = all_texts()
ENTRIES = reader.load_registry(REGISTRY_FILE)


def digest(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def test_every_eval_and_sample_text_is_covered():
    assert len(TEXTS) == len(GOLDEN["cases"]) == 120
    assert set(TEXTS) == set(GOLDEN["cases"])
    assert sum(k.startswith("samples/") for k in TEXTS) == 6


def test_registry_entries_match_the_old_loader_both_ways():
    assert ENTRIES == mock_model.load_registry(REGISTRY_FILE)
    assert reader.entries_from_registry(agencies.load_registry(REGISTRY_FILE)) == ENTRIES


@pytest.mark.parametrize("key", sorted(TEXTS))
def test_reader_equals_the_old_reader(key):
    new = reader.extract(TEXTS[key], ENTRIES)
    if mock_model.extract is not reader.extract:  # still a separate copy in eval/
        assert new == mock_model.extract(TEXTS[key], mock_model.load_registry(REGISTRY_FILE))
    if digest(ENTRIES) != GOLDEN["registry_entries_sha256"]:
        pytest.skip("registry.json changed since the golden hashes were recorded")
    assert digest(new) == GOLDEN["cases"][key]


def test_fit_schema_is_the_old_one():
    schema = pipeline.record_letter_tool(["irs"])["inputSchema"]["json"]
    data = reader.extract(TEXTS["samples/irs-balance-due"], ENTRIES)
    assert reader.fit_schema(data, schema) == mock_model.fit_schema(data, schema) == data


class OldReaderBedrock:
    """The AI_MODE=on fake the frozen eval used: answers record_letter with eval/mock_model.py."""

    def converse(self, **request):
        prompt = request["messages"][0]["content"][-1]["text"]
        document = prompt[prompt.find("<document>") + 10:prompt.find("</document>")].strip()
        data = mock_model.fit_schema(mock_model.extract(document, mock_model.load_registry(REGISTRY_FILE)),
                                     request["toolConfig"]["tools"][0]["toolSpec"]["inputSchema"]["json"])
        return {"output": {"message": {"content": [{"toolUse": {"name": "record_letter", "input": data}}]}},
                "usage": {"inputTokens": 1, "outputTokens": 1}}


def _comparable(result):
    result = json.loads(json.dumps(result))
    result.pop("trace"), result.pop("meta")
    result["grounding"].pop("source")
    for f in result["flags"]:
        f.pop("title"), f.pop("why")  # reworded for the rules reader; ids, severities and quotes must match
    return result


def test_check_off_equals_check_on_with_the_old_reader(monkeypatch):
    registry = agencies.load_registry(REGISTRY_FILE)
    request = {"today": TODAY.isoformat()}
    for key, text in TEXTS.items():
        monkeypatch.delenv("AI_MODE", raising=False)
        off = pipeline.check_request(pipeline.parse_check_request({**request, "text": text}), registry=registry)
        monkeypatch.setenv("AI_MODE", "on")
        monkeypatch.setattr(bedrock, "_client", OldReaderBedrock())
        on = pipeline.check_request(pipeline.parse_check_request({**request, "text": text}), registry=registry)
        assert _comparable(off) == _comparable(on), key
        assert off["meta"]["model"].startswith("rules-v") and on["meta"]["model"].startswith("us.amazon.nova")
