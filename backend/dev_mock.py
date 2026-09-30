"""Deterministic stand-ins for Textract and Bedrock, active when PLAINLY_MOCK=1.

They let the whole API run offline for UI work and tests. The fake extractor is deliberately crude
(keyword per line) and independent of verifier.py, so it does not just echo the rules back.

Knobs (environment):
  PLAINLY_MOCK_FAIL=textract|bedrock|both   make the fake service raise, to exercise degraded paths
  PLAINLY_MOCK_DELAY_MS=1500                sleep per call, to see loading states in the UI

Fake OCR text comes from, in order:
  1. image bytes containing b"PLAINLY-TEXT:" followed by UTF-8 text (tests build these),
  2. a sample letter whose rendered image matches the bytes (samples/letters/<id>.png|jpg next to
     <id>.txt or <id>.html),
  3. a built-in demo letter.
"""
import hashlib
import json
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples" / "letters"
TEXT_MARKER = b"PLAINLY-TEXT:"

DEMO_LETTER = """BSES Rajdhani Power Limited
ELECTRICITY DISCONNECTION NOTICE
Date: 29/09/2026
Dear Consumer, your electricity will be disconnected tonight at 9:30 PM because your last bill was not updated.
Pay Rs. 1,450 immediately via PhonePe to 98100 12345 to avoid disconnection.
Call our electricity officer on 98100 12345. Do not tell anyone about this notice.
SAMPLE - NOT A REAL NOTICE"""


class FakeServiceError(Exception):
    """Shaped like botocore's ClientError so callers classify it the same way."""

    def __init__(self, code, message):
        super().__init__(f"An error occurred ({code}): {message}")
        self.response = {"Error": {"Code": code, "Message": message}}


def _maybe_fail(service):
    fail = os.environ.get("PLAINLY_MOCK_FAIL", "")
    if fail in (service, "both"):
        raise FakeServiceError("ServiceUnavailableException", f"mock {service} failure")
    delay = int(os.environ.get("PLAINLY_MOCK_DELAY_MS", "0") or 0)
    if delay:
        time.sleep(delay / 1000)


def _html_to_text(html):
    html = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    html = re.sub(r"(?i)<br\s*/?>|</(p|div|h\d|li|tr|section|header|footer)>", "\n", html)
    text = re.sub(r"<[^>]+>", "", html)
    for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " "), ("&quot;", '"'),
                         ("&#39;", "'"), ("&mdash;", "-"), ("&rsquo;", "'")):
        text = text.replace(entity, char)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _sample_text_for(image_bytes):
    if not SAMPLES.is_dir():
        return None
    digest = hashlib.sha256(image_bytes).hexdigest()
    for image in list(SAMPLES.glob("*.png")) + list(SAMPLES.glob("*.jpg")):
        if hashlib.sha256(image.read_bytes()).hexdigest() != digest:
            continue
        for suffix, convert in ((".txt", lambda s: s), (".html", _html_to_text)):
            source = image.with_suffix(suffix)
            if source.exists():
                return convert(source.read_text(encoding="utf-8"))
    return None


def fake_ocr_text(image_bytes):
    marker = image_bytes.find(TEXT_MARKER)
    if marker != -1:
        return image_bytes[marker + len(TEXT_MARKER):].decode("utf-8", errors="ignore")
    return _sample_text_for(image_bytes) or DEMO_LETTER


class FakeTextract:
    def detect_document_text(self, Document):
        _maybe_fail("textract")
        text = fake_ocr_text(Document["Bytes"])
        # Like Textract, read nothing useful from Devanagari: keep only lines that are mostly Latin.
        lines = [line for line in text.splitlines() if line.strip() and _latin_share(line) > 0.5]
        blocks = [{"BlockType": "PAGE"}] + [{"BlockType": "LINE", "Text": line, "Confidence": 99.0} for line in lines]
        return {"Blocks": blocks, "DocumentMetadata": {"Pages": 1}}


def _latin_share(text):
    letters = [c for c in text if c.isalpha()]
    return sum(c.isascii() for c in letters) / len(letters) if letters else 1.0


class FakeBedrockRuntime:
    def converse(self, **request):
        _maybe_fail("bedrock")
        tool = request["toolConfig"]["tools"][0]["toolSpec"]["name"]
        prompt = "".join(block.get("text", "") for message in request["messages"] for block in message["content"])
        has_image = any("image" in block for message in request["messages"] for block in message["content"])
        if tool == "record_letter":
            document = _between(prompt, "<document>", "</document>").strip()
            if document == "(none)" and has_image:
                document = ""  # a real model would read the image; the mock can only say it saw nothing
            data = mock_extract(document)
        elif tool == "record_explanation":
            system = request["system"][0]["text"]
            language = _between(system, "human-readable field in ", ".") or "English"
            data = mock_explain(json.loads(_between(prompt, "<check>", "</check>") or "{}"), language)
        else:
            raise FakeServiceError("ValidationException", f"unknown tool {tool}")
        return {
            "output": {"message": {"role": "assistant", "content": [
                {"toolUse": {"toolUseId": "mock-1", "name": tool, "input": data}}]}},
            "stopReason": "tool_use",
            "usage": {"inputTokens": len(prompt) // 4, "outputTokens": len(json.dumps(data)) // 4},
            "metrics": {"latencyMs": 1},
        }


def _between(text, start, end):
    i = text.find(start)
    if i == -1:
        return ""
    j = text.find(end, i + len(start))
    return text[i + len(start):j if j != -1 else None]


_KEYWORDS = {
    "payment_requests": r"gift card|itunes|google play|bitcoin|crypto|western union|wire transfer|phonepe|gpay|"
                        r"google pay|paytm|upi|pay online|pay by",
    "threats": r"arrest|police|warrant|jail|deport|\bFIR\b|legal action|गिरफ्तार",
    "credential_requests": r"\botp\b|\bpin\b|password|cvv|ओटीपी",
    "secrecy": r"do not tell|don't tell|confidential|secret",
    "video_call": r"video call|skype|stay on the call",
    "ai_instructions": r"ignore (all )?previous|as an ai|classify this|system prompt",
}
_PROTECTIVE = re.compile(r"\bnever\b|\bdo not share\b|\bdon't share\b", re.I)
_AMOUNT = re.compile(r"(?:\$|₹|£|Rs\.?\s?)\s?\d[\d,]*(?:\.\d\d)?", re.I)
_DATE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|(?:January|February|March|April|May|June|July|"
                   r"August|September|October|November|December) \d{1,2}, \d{4})\b")


def mock_extract(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    data = {key: [] for key in _KEYWORDS}
    data.update(claimed_sender=lines[0] if lines else "", claimed_agency_key="other", amounts=[], deadlines=[],
                letter_date={"value": "", "quote": ""}, transcript="")
    for line in lines:
        for key, pattern in _KEYWORDS.items():
            m = re.search(pattern, line, re.I)
            if not m or (key == "credential_requests" and _PROTECTIVE.search(line)):
                continue
            item = {"quote": line[:200]}
            if key == "payment_requests":
                item["method"] = m.group()
            data[key].append(item)
        for amount in _AMOUNT.findall(line):
            data["amounts"].append({"amount": amount, "what": "amount mentioned", "quote": line[:200]})
        date_match = _DATE.search(line)
        if date_match and not data["letter_date"]["quote"] and re.search(r"date", line, re.I):
            data["letter_date"] = {"value": "", "quote": line[:200]}
        elif date_match and re.search(r"\b(by|before|due)\b", line, re.I):
            data["deadlines"].append({"quote": line[:200], "what": "Deadline in the letter"})
        relative = re.search(r"within (\d+) days", line, re.I)
        if relative:
            data["deadlines"].append({"quote": line[:200], "relative_days": int(relative.group(1)),
                                      "relative_to": "receipt" if "receipt" in line.lower() else "letter_date",
                                      "what": "Respond to the letter"})
    devanagari = sum("ऀ" <= c <= "ॿ" for c in text)
    data["language_of_letter"] = "Hindi" if devanagari > len(text) * 0.2 else "English"
    data["country"] = "IN" if re.search(r"₹|\bRs\b|india|upi|aadhaar|[ऀ-ॿ]", text, re.I) else \
        "UK" if re.search(r"£|hmrc|gov\.uk", text, re.I) else "US"
    return data


def mock_explain(brief, language):
    scam = brief.get("verdict") == "likely_scam"
    agency = brief.get("agency") or {}
    official = agency.get("official_phone") or agency.get("official_site") or "a number you look up yourself"
    channel = brief.get("report_channel") or {}
    tag = f"[mock {language}] "
    if scam:
        actions = [
            {"step": tag + "Do not pay", "how": "Do not send money, gift cards or codes.", "by": ""},
            {"step": tag + "Do not use the contacts in the letter", "how": "Don't call, click or reply.", "by": ""},
            {"step": tag + "Contact the agency yourself", "how": f"Use {official}.", "by": ""},
            {"step": tag + "Report it", "how": f"{channel.get('name', 'Local police')} {channel.get('url', '')}".strip(),
             "by": ""},
        ]
    else:
        actions = [{"step": tag + (d.get("what") or "Deadline"), "how": "See the letter.", "by": d.get("date")}
                   for d in brief.get("deadlines") or []]
        actions.append({"step": tag + "Confirm it is real", "how": f"Call {official}.", "by": ""})
    flags = brief.get("flags") or []
    return {
        "tldr": tag + (brief.get("headline") or ""),
        "explanation": [tag + f"{f['title']}. {f['why']}" for f in flags[:5]]
        or [tag + "We did not find warning signs in the wording."],
        "actions": actions,
        "jargon": [{"term": "Notice", "meaning": tag + "An official letter telling you something."}],
        "questions_to_ask": [tag + "Can you confirm you sent this letter?"],
        "reply_draft": "" if scam else (
            f"Dear {agency.get('name') or 'Sir or Madam'},\n\n{tag}I received your letter dated "
            f"{brief.get('letter_date') or '(date)'}. Please confirm the amount and the deadline.\n\nThank you."),
    }
