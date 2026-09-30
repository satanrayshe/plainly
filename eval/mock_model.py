"""A keyword stand-in for the Bedrock model, used when the pipeline runs offline.

It answers the two Converse calls the pipeline makes:
  - extract (forced tool `record_letter`): fields from the contract, each with a quote copied verbatim from the
    letter, found by plain keyword and date patterns;
  - narrate (any other tool, or no tool): a short, generic explanation built from the verdict it is shown.

This is deliberately simple. Offline eval numbers measure the deterministic rules plus this reader, not the
model, and eval/results.md says so. Nothing here imports backend code, so it cannot tune the rules.
"""
import json
import re
from datetime import date
from pathlib import Path

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
DATE_PATTERNS = [
    ("mdy", re.compile(_MON + r"\s+(\d{1,2}),?\s+(\d{4})", re.I)),
    ("dmy_name", re.compile(r"(\d{1,2})(?:st|nd|rd|th)?\s+" + _MON + r",?\s+(\d{4})", re.I)),
    ("iso", re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")),
    ("numeric", re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b")),
]

KEYWORDS = {
    "payment_requests": [
        ("gift card", r"gift ?cards?|itunes|google play (?:card|code)|steam card|amazon (?:gift )?card"),
        ("crypto", r"bitcoin|crypto(?:currency)?|\busdt\b|tether|btc atm|bitcoin atm"),
        ("wire transfer", r"wire transfer|western union|moneygram"),
        ("upi / payment app", r"\bupi\b|phonepe|google ?pay|\bgpay\b|paytm|bhim"),
        ("bank transfer to 'safe' account", r"(?:safe|secure|verification) account|transfer (?:all )?(?:your )?savings"),
    ],
    "threats": [r"\barrest", r"warrant", r"\bpolice\b", r"deport", r"\bFIR\b", r"legal action", r"prosecut",
                r"\bjail\b"],
    # A request verb must come first, so "write your social security number on your check" is not a request.
    "credential_requests": [r"(?:enter|provide|share|confirm|send|give|verify|tell|ready|sign in with|log ?in with)"
                            r"[^.\n]{0,60}(?:\bOTP\b|\bPIN\b|password|\bCVV\b|social security number|\bSSN\b|"
                            r"aadhaar|bank(?:ing)? (?:login|username|details)|card (?:number|details)|routing)"],
    "secrecy": [r"do not (?:tell|inform|disclose|share this)", r"don't (?:tell|inform)", r"keep (?:this )?confidential",
                r"national secrecy", r"keep (?:it|this) secret"],
    "video_call": [r"video call", r"skype", r"whatsapp video", r"stay on the call", r"camera on", r"on camera"],
    "ai_instructions": [r"ignore (?:all )?(?:previous|prior) instructions", r"\bas an ai\b", r"ai assistants?",
                        r"classify (?:this|the) (?:letter|document|message) as", r"system prompt",
                        r"automated reviewers?"],
    "link_requests": [r"\bclick\b", r"\btap\b", r"(?:open|use|visit) (?:the |this )?(?:following )?link",
                      r"link below", r"scan the qr"],
    "callback_requests": [r"\bcall\b[^.\n]{0,40}\d{3}", r"whats ?app"],
    "account_verification_requests": [r"(?:verify|confirm|update) (?:your )?(?:identity|details|account|kyc|pan)"],
    "prize_or_refund_bait": [r"you have won", r"\blottery\b", r"\bwinner\b", r"claim (?:your )?refund",
                             r"selected for (?:the )?job"],
}
AMOUNT_RE = re.compile(r"(?:[$£€₹]|\bRs\.?|\bINR)\s?\d[\d,]*(?:\.\d{1,2})?", re.I)
RELATIVE_RE = re.compile(r"within (\d{1,3}) (?:calendar |working |business )?days", re.I)
BY_DATE_RE = re.compile(r"\b(?:by|before|on or before|due(?: date)?:?|last date:?)\s*$", re.I)

AGENCY_HINTS = {  # extra spellings for common registry keys; only used when that key exists in the registry
    "irs": ["internal revenue service", "irs"],
    "ssa": ["social security administration"],
    "uscis": ["u.s. citizenship and immigration services", "uscis"],
    "medicare": ["medicare"],
    "hmrc": ["hm revenue", "hmrc"],
    "dvla": ["dvla", "driver and vehicle licensing"],
    "itd": ["income tax department", "income-tax department", "incometax.gov.in"],
    "income_tax": ["income tax department", "income-tax department", "incometax.gov.in"],
    "uidai": ["uidai", "unique identification authority"],
    "epfo": ["epfo", "employees' provident fund"],
    "trai": ["telecom regulatory authority", "trai"],
    "cbi": ["central bureau of investigation", "cbi"],
}


def load_registry(path):
    """Registry entries as [{key, names, country}] from a registry JSON file, whatever its outer shape."""
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        items = data.get("agencies", data)
        if isinstance(items, dict):
            items = [dict(v, key=v.get("key", k)) for k, v in items.items() if isinstance(v, dict)]
    else:
        items = data
    entries = []
    for item in items or []:
        if not isinstance(item, dict) or not item.get("key"):
            continue
        names = [item.get("name"), item.get("short_name")] + list(item.get("aliases") or item.get("names") or [])
        names += AGENCY_HINTS.get(item["key"], [])
        entries.append({"key": item["key"], "names": [n.lower() for n in names if n],
                        "country": item.get("country")})
    return entries


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]


def quote_for(match_start, match_end, text):
    """The sentence (or line) around a match, copied verbatim so grounding can find it."""
    start = max(text.rfind("\n", 0, match_start), max(text.rfind(p, 0, match_start) for p in (". ", "! ", "? ")) + 1)
    ends = [i for i in (text.find("\n", match_end), text.find(". ", match_end)) if i != -1]
    end = min(ends) + 1 if ends else len(text)
    quote = text[start:end].strip(" \n.")
    if len(quote) > 220:
        lo = max(0, match_start - start - 90)
        quote = quote[lo:lo + 220].strip()
    return quote


def find_all(patterns, text):
    found, seen = [], set()
    for pattern in patterns:
        for m in re.finditer(pattern, text, re.I):
            q = quote_for(m.start(), m.end(), text)
            if q and q not in seen:
                seen.add(q)
                found.append(q)
    return found


def parse_dates(text, country):
    out = []
    for kind, pattern in DATE_PATTERNS:
        for m in pattern.finditer(text):
            g = m.groups()
            try:
                if kind == "mdy":
                    d = date(int(g[2]), MONTHS[g[0][:3].lower()], int(g[1]))
                elif kind == "dmy_name":
                    d = date(int(g[2]), MONTHS[g[1][:3].lower()], int(g[0]))
                elif kind == "iso":
                    d = date(int(g[0]), int(g[1]), int(g[2]))
                else:
                    a, b, y = int(g[0]), int(g[1]), int(g[2])
                    day, month = (b, a) if (country == "US" and a <= 12) else (a, b)
                    d = date(y, month, day)
            except ValueError:
                continue
            out.append((m.start(), m.end(), d))
    return sorted(out)


def detect_country(text, agency_country):
    if agency_country:
        return agency_country
    if re.search(r"₹|\bRs\.?\s?\d|\bINR\b|aadhaar|\bupi\b|\bPAN\b|india", text, re.I):
        return "IN"
    if re.search(r"£|\bHMRC\b|\bDVLA\b|united kingdom", text, re.I):
        return "GB"
    return "US" if re.search(r"\$\s?\d|\bIRS\b|social security|\bU\.?S\.?\b", text) else "other"


# "Aadhaar number", "Aadhaar-linked", "Social Security number": an ID document named in the body, not the sender.
_ID_DOCUMENT_AFTER = re.compile(r"[\s-]*(?:numbers?|no\b|card|linked|details|seeded)")


def _sender(registry, lowered):
    """The registry agency named first in the text, which is where a letterhead or SMS sender sits."""
    best, best_at = None, None
    for agency in registry:
        for name in agency["names"]:
            for m in re.finditer(r"\b" + re.escape(name) + r"\b", lowered):
                if _ID_DOCUMENT_AFTER.match(lowered, m.end()):
                    continue
                if best_at is None or m.start() < best_at:
                    best, best_at = agency, m.start()
                break
    return best


def extract(text, registry):
    lowered = text.lower()
    agency = _sender(registry, lowered)
    country = detect_country(text, agency and agency["country"])
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    matched_name = next((n for n in (agency or {}).get("names", []) if n in lowered), None)

    dates = parse_dates(text, country)
    letter_date = None
    label = re.search(r"(notice date|date of issue|dated?)\b[:\s]*", text, re.I)
    if label:
        after = [d for d in dates if d[0] >= label.end() - 1]
        letter_date = after[0] if after else None
    letter_date = letter_date or (dates[0] if dates else None)

    deadlines = []
    for start, end, d in dates:
        if BY_DATE_RE.search(text[max(0, start - 20):start]):
            q = quote_for(start, end, text)
            deadlines.append({"quote": q, "absolute_date": d.isoformat(), "relative_days": None,
                              "relative_to": None, "what": q[:120]})
    for m in RELATIVE_RE.finditer(text):
        q = quote_for(m.start(), m.end(), text)
        anchored = re.search(r"date of (?:this|our|the) (?:notice|letter|communication)|date of issue|of (?:this|our) notice",
                             q, re.I)
        deadlines.append({"quote": q, "absolute_date": None, "relative_days": int(m.group(1)),
                          "relative_to": "letter_date" if anchored else "receipt", "what": q[:120]})

    def items(field):
        return [{"quote": q} for q in find_all(KEYWORDS[field], text)]

    payments = []
    for method, pattern in KEYWORDS["payment_requests"]:
        for q in find_all([pattern], text):
            payments.append({"method": method, "quote": q})

    return {
        "claimed_sender": matched_name.title() if matched_name else first_line[:80],
        "claimed_agency_key": agency["key"] if agency else "other",
        "country": country,
        "letter_date": {"value": letter_date[2].isoformat(), "quote": quote_for(letter_date[0], letter_date[1], text)}
        if letter_date else {"value": None, "quote": None},
        "deadlines": deadlines,
        "payment_requests": payments,
        "threats": items("threats"),
        "credential_requests": items("credential_requests"),
        "secrecy": items("secrecy"),
        "video_call": items("video_call"),
        "ai_instructions": items("ai_instructions"),
        "link_requests": items("link_requests"),
        "callback_requests": items("callback_requests"),
        "account_verification_requests": items("account_verification_requests"),
        "prize_or_refund_bait": items("prize_or_refund_bait"),
        "amounts": [{"amount": m.group(0), "what": "amount mentioned", "quote": quote_for(m.start(), m.end(), text)}
                    for m in AMOUNT_RE.finditer(text)][:6],
        "language_of_letter": "Hindi" if re.search(r"[ऀ-ॿ]", text) else "English",
    }


def narrate(prompt_text):
    verdict = re.search(r"\b(likely_scam|consistent_with_genuine|cant_tell)\b", prompt_text)
    verdict = verdict.group(1) if verdict else "cant_tell"
    language = re.search(r"\b(Hindi|Spanish|English|Tamil|Bengali|Marathi|Telugu|Gujarati|Punjabi|French)\b", prompt_text)
    dates = sorted(set(re.findall(r'"date":\s*"(\d{4}-\d{2}-\d{2})"', prompt_text)))
    scam = verdict == "likely_scam"
    return {
        "language": language.group(1) if language else "English",
        "tldr": ("This looks like a scam. Do not pay, call back or share any details."
                 if scam else "This letter asks you to act. Check it on the official number before you do anything."),
        "explanation": ["[offline mock narration] The checker's verdict is " + verdict.replace("_", " ") + ".",
                        "Each warning sign is quoted from the letter above.",
                        "Use only the official phone number or website, never the ones printed on the letter."],
        "actions": ([{"step": "Do not pay or reply", "how": "Ignore the numbers and links in the letter.", "by": None},
                     {"step": "Report it", "how": "Use the reporting channel shown with the result.", "by": None}]
                    if scam else [{"step": "Confirm the letter", "how": "Call the official number shown.",
                                   "by": dates[0] if dates else None}]),
        "jargon": [],
        "questions_to_ask": ["Is this letter on my account?"],
        "reply_draft": "" if scam else "Hello, I received your letter and would like to confirm the details. Thank you.",
    }


def fit_schema(values, schema):
    """Shape a dict to a tool's JSON schema: keep known keys, fill required ones with empty values."""
    props = (schema or {}).get("properties") or {}
    if not props:
        return values
    empty = {"string": "", "array": [], "object": {}, "integer": 0, "number": 0, "boolean": False}
    out = {k: v for k, v in values.items() if k in props}
    for key in (schema.get("required") or []):
        if key not in out:
            kind = props.get(key, {}).get("type", "string")
            out[key] = None if isinstance(kind, list) and "null" in kind else empty.get(kind if isinstance(kind, str) else kind[0], "")
    return out
