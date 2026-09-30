"""Deterministic verdict: rules, registry checks, quote grounding, date math and the receipts trace.

Code decides the verdict. The model only proposes quotes (see pipeline.extract); every model quote is checked
against the independently read text before it can count at full strength.
"""
import re
import time
from datetime import date, timedelta

import agencies
import contacts
import dates
import grounding
import lexicon

VERDICTS = ("likely_scam", "consistent_with_genuine", "cant_tell")
POINTS = {"strong": 3, "medium": 1, "info": 0}
SCAM_SCORE = 3
GROUNDED_SHARE_FOR_GENUINE = 0.8
_SEVERITY_ORDER = {"strong": 0, "medium": 1, "info": 2}

_FTC_IMPOSTER = {"name": "FTC", "url": "https://consumer.ftc.gov/articles/how-avoid-government-impersonator-scam"}
_FTC_PHISHING = {"name": "FTC", "url": "https://consumer.ftc.gov/articles/how-recognize-avoid-phishing-scams"}
_FTC_GIFT = {"name": "FTC", "url": "https://consumer.ftc.gov/articles/avoiding-and-reporting-gift-card-scams"}
_FTC_CRYPTO = {"name": "FTC", "url": "https://consumer.ftc.gov/articles/what-know-about-cryptocurrency-scams"}
_RBI = {"name": "Reserve Bank of India (RBI Kehta Hai)", "url": "https://rbikehtahai.rbi.org.in/"}
_NCRP = {"name": "National Cyber Crime Reporting Portal", "url": "https://cybercrime.gov.in"}
_NCSC = {"name": "UK National Cyber Security Centre", "url": "https://www.ncsc.gov.uk/collection/phishing-scams"}
_OWASP = {"name": "OWASP GenAI Security Project", "url": "https://genai.owasp.org/llmrisk/llm01-prompt-injection/"}

RULES = {
    "payment_gift_card": {
        "severity": "strong", "title": "Asks for payment by gift card",
        "why": "Real government offices and utilities never take gift cards. Asking for them is a classic scam sign.",
        "sources": {"default": _FTC_GIFT},
    },
    "payment_crypto_wire": {
        "severity": "strong", "title": "Asks for crypto, a wire transfer or a \"safe account\"",
        "why": "Agencies don't collect money in cryptocurrency, by Western Union or MoneyGram, or into a "
               "\"safe account\". Money sent this way is almost impossible to get back.",
        "sources": {"default": _FTC_CRYPTO, "IN": _RBI},
    },
    "payment_personal_upi": {
        "severity": "strong", "title": "Asks you to pay a personal UPI ID or phone number",
        "why": "A government office or power company collects money through its own official payment page, "
               "not to a person's UPI ID or mobile number.",
        "sources": {"default": _RBI},
    },
    "credential_request": {
        "severity": "strong", "title": "Asks for an OTP, PIN, password or full ID number",
        "why": "No real agency or bank asks you to share an OTP, PIN, password or your full SSN or Aadhaar. "
               "Anyone who has them can empty your accounts.",
        "sources": {"default": _FTC_PHISHING, "IN": _RBI, "UK": _NCSC},
    },
    "threat_arrest": {
        "severity": "strong", "title": "Threatens arrest, police action or deportation",
        "why": "Agencies write to you and give you time to respond. Threats of arrest or police if you don't pay "
               "right now are a pressure tactic.",
        "sources": {"default": _FTC_IMPOSTER, "IN": _NCRP, "UK": _NCSC},
    },
    "video_call_demand": {
        "severity": "strong", "title": "Demands a video call or that you stay on the line",
        "why": "Police and agencies do not question or \"arrest\" people over video calls. A so-called digital "
               "arrest is a scam.",
        "sources": {"default": _FTC_IMPOSTER, "IN": _NCRP},
    },
    "ai_instruction": {
        "severity": "strong", "title": "Contains hidden instructions aimed at AI tools",
        "why": "A genuine letter has no reason to talk to AI tools. Text like this tries to trick scam checkers, "
               "so we treat it as a strong warning sign and do not repeat it.",
        "sources": {"default": _OWASP},
    },
    "lookalike_domain": {
        "severity": "strong", "title": "Uses a web or email address that imitates an official one",
        "why": "Scammers register addresses that look like the real one at a glance.",
        "sources": {"default": _FTC_PHISHING, "UK": _NCSC},
    },
    "urgency_short": {
        "severity": "medium", "title": "Gives you less than 3 days to act",
        "why": "Very short deadlines are meant to rush you. Genuine notices usually give you weeks.",
        "sources": {"default": _FTC_IMPOSTER, "IN": _NCRP, "UK": _NCSC},
    },
    "freemail_official": {
        "severity": "medium", "title": "Gives a free email address as an official contact",
        "why": "Government offices and companies use their own email domains, not Gmail, Yahoo or Outlook.",
        "sources": {"default": _FTC_PHISHING, "UK": _NCSC},
    },
    "secrecy": {
        "severity": "medium", "title": "Tells you to keep it secret",
        "why": "Scammers tell you not to talk to family or your bank because those people would stop you.",
        "sources": {"default": _FTC_IMPOSTER, "IN": _NCRP},
    },
    "unknown_contact": {
        "severity": "info", "title": "Contact details are not on the official list",
        "why": "We only hold official contacts for a short list of agencies. That alone does not make it a scam.",
        "sources": {"default": _FTC_IMPOSTER},
    },
    "injection_detected_model": {
        "severity": "info", "title": "The AI reader noticed instructions aimed at AI tools",
        "why": "The model that read the letter reported text addressed to AI tools. We do not repeat it.",
        "sources": {"default": _OWASP},
    },
}

_CLAUSE_BREAKS = ".!?\n।:;,"
_SENTENCE_BREAKS = ".!?\n।;"
_NEAR_NEGATION_WORDS = 3
_LIST_ITEM_WORDS = 6
MAX_QUOTES_PER_RULE = 4
_QUOTE_EDGES = " \t\r•·*-–—"
# "Gift cards are not accepted": the negation follows the match directly.
_AFTER_NEGATION = re.compile(r"^\s*(?:\w+\s+)?(?:(?:are|is|will|should|must|can|do|does)\s+(?:never|not)\b"
                             r"|(?:are|is|will|should|must|can|do|does|wo|ca)n't\b|not\s+(?:be\s+)?"
                             r"(?:accepted|required|requested)\b)", re.I)
_CANNOT_PAY = re.compile(r"\b(?:can't|cannot|can\s+not|unable\s+to|not\s+able\s+to)\s+pay\b", re.I)


# ---------------------------------------------------------------- model output coercion

def _s(value, limit=300):
    return value.strip()[:limit] if isinstance(value, str) else ""


def _quote_items(raw, key, extra=(), numbers=()):
    value = raw.get(key)
    items = []
    for item in value[:12] if isinstance(value, list) else []:
        if isinstance(item, str):
            item = {"quote": item}
        if not isinstance(item, dict):
            continue
        entry = {"quote": _s(item.get("quote"))}
        for field in extra:
            entry[field] = _s(item.get(field), 200)
        for field in numbers:
            entry[field] = _int_or_none(item.get(field))
        if entry["quote"] or any(entry.get(f) for f in extra):
            items.append(entry)
    return items


def _int_or_none(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def normalize_extraction(raw):
    """Coerce whatever the model returned into the shape the rules expect. Never raises."""
    raw = raw if isinstance(raw, dict) else {}
    letter_date = raw.get("letter_date")
    if isinstance(letter_date, str):
        letter_date = {"value": letter_date, "quote": ""}
    letter_date = letter_date if isinstance(letter_date, dict) else {}
    country = _s(raw.get("country"), 10).upper()
    country = {"GB": "UK", "USA": "US", "INDIA": "IN", "IND": "IN"}.get(country, country)
    deadlines = _quote_items(raw, "deadlines", ("absolute_date", "relative_to", "what"), ("relative_days",))
    return {
        "claimed_sender": _s(raw.get("claimed_sender"), 200),
        "claimed_agency_key": _s(raw.get("claimed_agency_key"), 40).lower(),
        "country": country if country in ("US", "IN", "UK") else "",
        "letter_date": {"value": _s(letter_date.get("value"), 40), "quote": _s(letter_date.get("quote"))},
        "deadlines": deadlines,
        "payment_requests": _quote_items(raw, "payment_requests", ("method",)),
        "threats": _quote_items(raw, "threats"),
        "credential_requests": _quote_items(raw, "credential_requests"),
        "secrecy": _quote_items(raw, "secrecy"),
        "video_call": _quote_items(raw, "video_call"),
        "ai_instructions": _quote_items(raw, "ai_instructions"),
        "amounts": _quote_items(raw, "amounts", ("amount", "what")),
        "language_of_letter": _s(raw.get("language_of_letter"), 40),
        "transcript": _s(raw.get("transcript"), 20000),
    }


# ---------------------------------------------------------------- text helpers

def snippet(text, start, end, limit=240):
    """The line around a match (or a trimmed window of it when the line is long, as in pasted SMS)."""
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    line_end = len(text) if line_end == -1 else line_end
    if line_end - line_start <= limit:
        return text[line_start:line_end].strip(_QUOTE_EDGES)
    sentence_start = max([line_start] + [text.rfind(c, line_start, start) + 1 for c in ".!?।"])
    ends = [i for i in (text.find(c, end, line_end) for c in ".!?।") if i != -1]
    sentence_end = min(ends) + 1 if ends else line_end
    if sentence_end - sentence_start <= limit:
        return text[sentence_start:sentence_end].strip()
    lo = max(line_start, start - (limit - (end - start)) // 2)
    return text[lo:min(line_end, lo + limit)].strip()


def _negated(text, start, end):
    """True when a match sits in protective wording ("we will never ask for gift cards")."""
    sentence_start = max(text.rfind(c, 0, start) for c in _SENTENCE_BREAKS) + 1
    prefix = text[sentence_start:start]
    negations = list(lexicon.NEGATION.finditer(prefix))
    if negations:
        neg = negations[-1]
        clause_before = re.split(r"[,:]", prefix[:neg.start()])[-1]
        between = prefix[neg.end():]
        if (not lexicon.CONDITIONAL.search(clause_before) and not lexicon.RESUMES.search(between)
                and _negation_covers(between)):
            return True
    return bool(_AFTER_NEGATION.search(text[end:]))


def _negation_covers(between):
    """Does a negation reach the match, given the words between them?

    Close by in the same clause ("do not pay with gift cards"), or through a negated verb such as ask, demand or
    accept followed by a plain list ("never demand ... such as a prepaid card, gift card or wire transfer").
    "You did not respond to our notices so a warrant ..." is neither.
    """
    parts = re.split(r"[,:]", between)
    if len(parts) == 1 and len(between.split()) <= _NEAR_NEGATION_WORDS:
        return True
    return bool(lexicon.PROTECTIVE_VERB.match(parts[0])) and all(
        len(p.split()) <= _LIST_ITEM_WORDS for p in parts[1:])


def _first(regex, text, *, negatable=True, accept=None):
    for m in regex.finditer(text):
        if negatable and _negated(text, m.start(), m.end()):
            continue
        if accept and not accept(m):
            continue
        return m
    return None


# ---------------------------------------------------------------- the check

class _Check:
    """Per-letter state shared by the rules."""

    def __init__(self, text, ex, source, today, registry, independent_text=None):
        self.text = text
        self.ex = ex
        self.source = source
        self.independent = source in ("textract", "pasted_text")
        # Partial: `text` is the independent reading followed by the model's transcript of what that reader
        # could not read (e.g. a Hindi body under an English letterhead). Only the first part can ground.
        reader_text = text if independent_text is None else independent_text
        self.partial = self.independent and len(reader_text) < len(text)
        self.independent_end = len(reader_text)
        self.reader = grounding.Reader(reader_text) if self.independent else None
        self.reader_script_share = _non_latin_share(reader_text) if self.partial else 0.0
        self.today = today
        self.registry = registry
        self.grounded = 0
        self.checked = 0
        self.unverified = 0
        self.flags = []
        self.trace = []
        self.country = ex["country"]

    def ground(self, quote):
        """True/False against the independent text; None when there is no independent reader for it."""
        if not self.independent:
            if quote:
                self.checked += 1
            return None
        if not quote:
            return False
        if self.partial and _non_latin_share(quote) > 0.5 and self.reader_script_share < 0.2:
            self.unverified += 1
            return None  # a script the independent reader cannot read; don't count it against the letter
        self.checked += 1
        ok = self.reader.is_grounded(quote)
        self.grounded += ok
        return ok

    def code_grounded(self, position=None):
        """Grounding of a quote the code itself found at `position` in the text (None or -1: unknown)."""
        if not self.independent:
            return None
        if self.partial and (position is None or not 0 <= position < self.independent_end):
            return None
        return True

    def add_trace(self, step, status, detail, started=None):
        ms = int((time.perf_counter() - started) * 1000) if started else 0
        self.trace.append({"step": step, "status": status, "detail": detail, "ms": ms})

    def flag(self, rule, *, quote, grounded, why=None, severity=None, redacted=False):
        meta = RULES[rule]
        severity = severity or meta["severity"]
        if grounded is False and severity == "strong":
            severity = "medium"  # the model quoted something the independent reader never saw
        sources = meta["sources"]
        self.flags.append({
            "rule": rule,
            "severity": severity,
            "title": meta["title"],
            "quote": None if redacted else (quote or None),
            "quote_redacted": bool(redacted),
            "grounded": grounded,
            "why": why or meta["why"],
            "source": sources.get(self.country) or sources["default"],
        })

    def model_quote(self, items, accept=None):
        """Best model quote for a rule: grounded ones first. -> (quote, grounded) or (None, None)."""
        fallback = None
        tried = 0
        for item in items:
            quote = item.get("quote") or ""
            if not quote or (accept and not accept(item)):
                continue
            if tried == MAX_QUOTES_PER_RULE:
                break
            tried += 1
            ok = self.ground(quote)
            if ok or ok is None:
                return quote, ok
            fallback = fallback or (quote, ok)
        return fallback or (None, None)


def _rule(check, rule, *, regex=None, model_items=(), negatable=True, accept=None, model_accept=None,
          found_detail="Found in the letter", pass_detail="Nothing like this in the letter"):
    """Shared shape for the phrase rules: code regex on the text first, model quotes second."""
    started = time.perf_counter()
    m = _first(regex, check.text, negatable=negatable, accept=accept) if regex is not None else None
    step = f"rule:{rule}"
    if m:
        check.flag(rule, quote=snippet(check.text, m.start(), m.end()), grounded=check.code_grounded(m.start()))
        check.add_trace(step, "flag", found_detail, started)
        return True
    quote, ok = check.model_quote(model_items, model_accept)
    if quote:
        check.flag(rule, quote=quote, grounded=ok)
        note = {True: "quote confirmed in the independently read text",
                False: "quote NOT found in the independently read text, so it counts as medium",
                None: "not independently grounded"}[ok]
        check.add_trace(step, "flag", f"Reported by the model; {note}", started)
        return True
    check.add_trace(step, "pass", pass_detail, started)
    return False


def _claims(check, regex, agency):
    header = "\n".join(check.text.splitlines()[:6])
    return bool(agency) or bool(regex.search(check.ex["claimed_sender"])) or bool(regex.search(header))


def verify(letter_text, extraction=None, *, grounding_source="textract", today=None, registry=None,
           independent_text=None):
    """Run every rule and return the verdict block of the /api/check response (plus redacted letter_text).

    independent_text: when letter_text is the OCR text plus a model transcript appended after it, the OCR part
    alone. Quotes are then grounded only against that part.
    """
    registry = registry or agencies.load_registry()
    today = today or date.today()
    ex = normalize_extraction(extraction)
    text = letter_text or ""
    check = _Check(text, ex, grounding_source, today, registry, independent_text)

    # -- contacts found by code, never by the model
    started = time.perf_counter()
    phones = _unique([p for p, _, _ in contacts.find_phones(text)], key=contacts.phone_key)
    urls = _unique([u for u, _, _ in contacts.find_urls(text)])
    emails = _unique([e for e, _, _ in contacts.find_emails(text)], key=str.lower)
    email_hosts = [contacts.host_of(e.split("@", 1)[1]) for e in emails]
    hosts = _unique([contacts.host_of(u) for u in urls] + email_hosts)

    agency, how = agencies.match_agency(
        registry, claimed_key=ex["claimed_agency_key"], claimed_sender=ex["claimed_sender"], text=text,
        hosts=hosts, phones=phones, trust_model_key=not check.independent)
    if agency:
        check.country = agency.get("country") or check.country
        check.add_trace("registry", "done", f"Matched {agency['name']} because {how}. Official contacts from "
                                            f"{agency.get('source_url')} (checked {agency.get('checked_on')}).",
                        started)
    else:
        check.add_trace("registry", "unknown", f"No match: {how}.", started)

    phones = [p for p in phones if contacts.plausible_for_country(p, check.country)]
    short_official = agencies.official_phone_hits(agency, phones, text) if agency else []
    phones_out = phones + [p for p in short_official if len(re.sub(r"\D", "", p)) < 8]
    check.add_trace("contacts", "done", f"Found {len(phones_out)} phone number(s), {len(urls)} link(s) and "
                                        f"{len(emails)} email address(es) in the text.")

    # -- dates first: the urgency rule needs to know whether a real deadline exists
    dates_started = time.perf_counter()
    letter_date, letter_date_how = _letter_date(check)
    deadlines = _deadlines(check, letter_date)
    dates_ms = time.perf_counter() - dates_started

    # -- rules, in contract order
    _rule(check, "payment_gift_card", regex=lexicon.GIFT_CARD, model_items=ex["payment_requests"],
          model_accept=lambda i: bool(lexicon.GIFT_CARD.search(f"{i.get('method')} {i.get('quote')}")),
          found_detail="The letter asks for gift cards", pass_detail="No gift-card payment requested")
    _rule(check, "payment_crypto_wire", regex=lexicon.CRYPTO_WIRE, model_items=ex["payment_requests"],
          model_accept=lambda i: bool(lexicon.CRYPTO_WIRE.search(f"{i.get('method')} {i.get('quote')}")),
          found_detail="The letter asks for crypto, a wire transfer or a \"safe account\"",
          pass_detail="No crypto, wire or \"safe account\" payment requested")
    _rule_upi(check, agency)
    _rule(check, "credential_request", regex=lexicon.CREDENTIAL_REQUEST, negatable=False,
          accept=lambda m: _is_credential_request(check, m), model_items=ex["credential_requests"],
          found_detail="The letter asks you to share a secret code or ID number",
          pass_detail="No request for an OTP, PIN, password or full ID number")
    _rule(check, "threat_arrest", regex=lexicon.THREAT, model_items=ex["threats"],
          found_detail="The letter threatens arrest, police or legal action",
          pass_detail="No threat of arrest, police or deportation")
    _rule_video(check)
    _rule_ai_instruction(check)
    lookalike_hosts = _rule_lookalike(check, hosts)
    _rule_urgency(check, _has_real_deadline(deadlines, letter_date or check.today))
    freemail_hosts = _rule_freemail(check, emails, agency)
    _rule(check, "secrecy", regex=lexicon.SECRECY, negatable=False, model_items=ex["secrecy"],
          accept=lambda m: not lexicon.CREDENTIAL_WORD.search(check.text[m.start():m.end() + 30]),
          found_detail="The letter tells you to keep this to yourself", pass_detail="No request for secrecy")
    official_hits = _rule_unknown_contact(check, agency, phones, hosts, short_official,
                                          skip=set(lookalike_hosts) | set(freemail_hosts))
    _rule_injection_model(check)

    _urgency_from_deadlines(check, letter_date, deadlines)
    detail = (f"Letter date {letter_date.isoformat()} ({letter_date_how}). " if letter_date
              else "No letter date found. ")
    detail += f"{len(deadlines)} deadline(s) worked out in code." if deadlines else "No deadlines found."
    check.add_trace("dates", "done", detail)
    check.trace[-1]["ms"] = int(dates_ms * 1000)
    amounts = _amounts(check)

    # -- grounding summary
    if check.independent:
        g_detail = (f"{check.grounded} of {check.checked} model quote(s) found in the "
                    f"{'Textract' if grounding_source == 'textract' else 'pasted'} text.")
        if check.partial:
            g_detail += (f" Part of the letter was read by the AI model only (a script the independent reader "
                         f"cannot read), so {check.unverified} quote(s) from it could not be checked.")
        if check.reader.out_of_time:
            g_detail += " Fuzzy matching hit its time limit, so some quotes were only checked word for word."
    else:
        g_detail = "Not independently grounded: no second reader could read this letter's text."
    check.add_trace("grounding", "done" if check.independent else "unknown", g_detail)

    redacted_text = _redact(text, ex)
    for f in check.flags:
        if f["quote"] and lexicon.AI_INSTRUCTION.search(f["quote"]):
            f["quote"], f["quote_redacted"] = None, True
    check.flags.sort(key=lambda f: _SEVERITY_ORDER[f["severity"]])

    verdict = _verdict(check, agency, official_hits)
    country = check.country or (agency or {}).get("country")
    return {
        **verdict,
        "agency": agencies.public_view(registry, agency) if agency else None,
        "report_channel": agencies.report_channel(registry, country),
        "flags": check.flags,
        "trace": check.trace,
        "extracted": {
            "claimed_sender": ex["claimed_sender"] or None,
            "letter_date": letter_date.isoformat() if letter_date else None,
            "phones": phones_out,
            "urls": urls,
            "emails": emails,
            "amounts": amounts,
            "deadlines": [_redact_deadline(d) for d in deadlines],
        },
        "letter_text": redacted_text,
        "grounding": {"source": grounding_source, "grounded": check.grounded, "total": check.checked,
                      **({"partial": True, "unverified": check.unverified} if check.partial else {})},
    }


def _unique(items, key=lambda x: x):
    seen, out = set(), []
    for item in items:
        k = key(item)
        if k not in seen:
            seen.add(k)
            out.append(item)
    return out


def _non_latin_share(text):
    """Share of letters outside the Latin script (Devanagari, for instance)."""
    letters = [c for c in text or "" if c.isalpha()]
    return sum(ord(c) > 0x24F for c in letters) / len(letters) if letters else 0.0


_SENTENCE_END = re.compile(r"[!?\n।]|\.(?=\s|$)")  # a dot inside irs.gov/account does not end a sentence


def _sentence_around(text, start, end):
    before = [m.end() for m in _SENTENCE_END.finditer(text, 0, start)]
    after = _SENTENCE_END.search(text, end)
    return text[before[-1] if before else 0:after.start() if after else len(text)]


def _line_context(text, start, end, before=120, after=60):
    """The words around a match on its own line: "Pay Rs. 2515 by UPI to x@okicici" is one payment, whatever the
    abbreviation dots in between."""
    lo = max(text.rfind("\n", 0, start) + 1, start - before)
    line_end = text.find("\n", end)
    return text[lo:min(len(text) if line_end == -1 else line_end, end + after)]


def _is_credential_request(check, m):
    """Asks the reader to hand over a secret, as opposed to warning them not to, or to sign in themselves."""
    text = check.text
    verb_start = m.start("verb") if m.group("verb") else m.start("verb2")
    if lexicon.VERB_NEGATION.search(text[max(0, verb_start - 80):verb_start]):
        return False
    verb = m.group("verb") or m.group("verb2")
    if not lexicon.ENTRY_VERB_WORD.fullmatch(verb):
        return True
    sentence = _sentence_around(text, m.start(), m.end())
    return not (lexicon.OFFICIAL_PORTAL.search(sentence) or any(
        _official_host(check, contacts.host_of(url)) for url, _, _ in contacts.find_urls(sentence)))


def _official_host(check, host):
    return contacts.is_government(host) or any(
        contacts.on_domain(host, d) for d in agencies.all_domains(check.registry))


# ---------------------------------------------------------------- individual rules

def _own_names(check, agency):
    """Words a merchant UPI handle of the claimed sender would contain (bsesrajdhani@hdfcbank for BSES Rajdhani)."""
    if agency:
        domains = agency.get("domains", [])
        names = {w for w, d in agencies.brand_words(check.registry).items() if d in domains}
        return names | {contacts.split_host(d)[0] for d in domains if contacts.split_host(d)[0]}
    # No registry match (most utilities): use the sender's own name as the letter gives it.
    sender = check.ex["claimed_sender"] + "\n" + "\n".join(check.text.splitlines()[:3])
    sender = contacts.UPI_RE.sub(" ", sender)  # a handle must not vouch for itself
    words ={w for w in re.findall(r"[a-z]{4,}", sender.lower()) if w not in lexicon.GENERIC_NAME_WORDS}
    compact = re.sub(r"[^a-z0-9]", "", check.ex["claimed_sender"].lower())
    return words | ({compact} if len(compact) >= 4 else set())


def _rule_upi(check, agency):
    started = time.perf_counter()
    text = check.text
    own_names = _own_names(check, agency)
    quote = position = None
    severity = "strong"
    for vpa, start, end in contacts.find_upi_ids(text):
        handle, provider = vpa.lower().split("@", 1)
        near = text[max(0, start - 60):end + 60]
        if provider not in lexicon.UPI_PROVIDERS and not lexicon.UPI_CONTEXT.search(near):
            continue
        if any(name and name in handle for name in own_names):
            continue  # merchant handle in the sender's own name, e.g. bsesrajdhani@hdfcbank
        quote, position = snippet(text, start, end), start
        # A mobile number as the handle, or "pay/send ... to" it, is a payment to a person. A bare handle that
        # merely appears is suspicious, not damning: it may be a merchant ID we can't tie to the sender.
        personal = re.search(r"[6-9]\d{9}", handle) or lexicon.PAY_VERB.search(_line_context(text, start, end))
        severity = "strong" if personal else "medium"
        break
    if quote is None:
        m = _first(lexicon.PAYMENT_APP_TO_MOBILE, text,
                   accept=lambda m: bool(lexicon.PAY_VERB.search(_line_context(text, m.start(), m.end()))))
        if m:
            quote, position = snippet(text, m.start(), m.end()), m.start()
    grounded = check.code_grounded(position) if quote else None
    if quote is None:
        quote, grounded = check.model_quote(
            check.ex["payment_requests"],
            lambda i: bool(re.search(r"upi|phone\s*pe|g\s?pay|google\s*pay|paytm|bhim", i.get("method", ""), re.I))
            and bool(contacts.UPI_RE.search(i["quote"]) or re.search(r"[6-9]\d{4}[\s-]?\d{5}", i["quote"])))
    if quote is None:
        check.add_trace("rule:payment_personal_upi", "pass", "No payment to a personal UPI ID or mobile number",
                        started)
    elif not _claims(check, lexicon.GOVERNMENT_OR_UTILITY, agency):
        check.add_trace("rule:payment_personal_upi", "pass", "A UPI ID appears, but the letter does not claim to be "
                                                              "from a government body or utility", started)
    else:
        check.flag("payment_personal_upi", quote=quote, grounded=grounded, severity=severity)
        check.add_trace("rule:payment_personal_upi", "flag", "A government body or utility would not ask for "
                                                              "payment to a personal UPI ID or number", started)


def _rule_video(check):
    started = time.perf_counter()
    text = check.text
    m = _first(lexicon.VIDEO_CALL, text,
               accept=lambda m: not lexicon.VIDEO_KYC.search(text[max(0, m.start() - 20):m.end() + 20]))
    m = m or _first(lexicon.STAY_ON_CALL, text, negatable=False)
    if m:
        check.flag("video_call_demand", quote=snippet(text, m.start(), m.end()),
                   grounded=check.code_grounded(m.start()))
        check.add_trace("rule:video_call_demand", "flag", "The letter asks for a video call or to stay on the line",
                        started)
        return
    quote, ok = check.model_quote(check.ex["video_call"])
    if quote:
        check.flag("video_call_demand", quote=quote, grounded=ok)
        check.add_trace("rule:video_call_demand", "flag", "Reported by the model", started)
    else:
        check.add_trace("rule:video_call_demand", "pass", "No video-call demand", started)


def _rule_ai_instruction(check):
    started = time.perf_counter()
    m = lexicon.AI_INSTRUCTION.search(check.text)
    if m:
        check.flag("ai_instruction", quote=None, grounded=check.code_grounded(m.start()), redacted=True)
        check.add_trace("rule:ai_instruction", "flag", "Text addressed to AI tools found (redacted, never shown)",
                        started)
    else:
        check.add_trace("rule:ai_instruction", "pass", "No text addressed to AI tools", started)


def _rule_lookalike(check, hosts):
    started = time.perf_counter()
    domains = agencies.all_domains(check.registry)
    words = agencies.brand_words(check.registry)
    found = []
    for host in hosts:
        reason = contacts.lookalike_reason(host, domains, words)
        if reason:
            found.append((host, reason))
    if not hosts:
        check.add_trace("rule:lookalike_domain", "pass", "No links or email addresses to check", started)
        return []
    if not found:
        check.add_trace("rule:lookalike_domain", "pass",
                        f"{len(hosts)} address(es) checked against {len(domains)} official domains", started)
        return []
    host, reason = found[0]
    idx = check.text.lower().find(host)
    quote = snippet(check.text, idx, idx + len(host)) if idx >= 0 else host
    check.flag("lookalike_domain", quote=quote, grounded=check.code_grounded(idx),
               why=f"The address {host} {reason}. Scammers register addresses like this to look official.")
    check.add_trace("rule:lookalike_domain", "flag", "; ".join(f"{h} {r}" for h, r in found), started)
    return [h for h, _ in found]


def _has_real_deadline(deadlines, since):
    return any((date.fromisoformat(d["date"]) - since).days >= 3 for d in deadlines)


def _rule_urgency(check, real_deadline):
    started = time.perf_counter()

    def short_enough(m):
        hours = m.groupdict().get("hours") or m.groupdict().get("hours_hi")
        if hours is not None and int(hours) >= 72:
            return False
        # "If you can't pay the full amount immediately, ..." offers help; it doesn't set a deadline.
        clause_start = max(check.text.rfind(c, 0, m.start()) for c in _CLAUSE_BREAKS) + 1
        return not _CANNOT_PAY.search(check.text[clause_start:m.start()])

    m = _first(lexicon.URGENCY, check.text, accept=short_enough)
    if not m and not real_deadline:
        m = _first(lexicon.SOFT_URGENCY, check.text, accept=short_enough)
    if m:
        check.flag("urgency_short", quote=snippet(check.text, m.start(), m.end()),
                   grounded=check.code_grounded(m.start()))
        check.add_trace("rule:urgency_short", "flag", "The letter demands action within hours or today", started)
    else:
        check.add_trace("rule:urgency_short", "pass", "No demand to act within 72 hours in the wording", started)


def _urgency_from_deadlines(check, letter_date, deadlines):
    if not letter_date or any(f["rule"] == "urgency_short" for f in check.flags):
        return
    for d in deadlines:
        gap = (date.fromisoformat(d["date"]) - letter_date).days
        if 0 <= gap < 3:
            check.flag("urgency_short", quote=d["quote"],
                       grounded=check.code_grounded(check.text.find(d["quote"])),
                       why=f"The deadline is {gap} day(s) after the letter's own date. Genuine notices usually "
                           f"give you weeks.")
            for entry in check.trace:
                if entry["step"] == "rule:urgency_short":
                    entry.update(status="flag", detail=f"Deadline {d['date']} is {gap} day(s) after the letter date")
            return


def _rule_freemail(check, emails, agency):
    started = time.perf_counter()
    free = [e for e in emails if contacts.is_freemail(e.split("@", 1)[1])]
    if not free:
        check.add_trace("rule:freemail_official", "pass", "No free email address given", started)
        return []
    if not _claims(check, lexicon.ORGANISATION, agency):
        check.add_trace("rule:freemail_official", "pass", "A free email address appears, but the letter does not "
                                                          "claim to come from an organisation", started)
        return []
    idx = check.text.find(free[0])
    check.flag("freemail_official", quote=snippet(check.text, idx, idx + len(free[0])),
               grounded=check.code_grounded(idx))
    check.add_trace("rule:freemail_official", "flag", f"{free[0].split('@', 1)[1]} is a free email service",
                    started)
    return [contacts.host_of(e.split("@", 1)[1]) for e in free]


def _rule_unknown_contact(check, agency, phones, hosts, short_official, skip):
    """Registry comparison. Domains first, then phones. Returns the official contacts found in the letter."""
    started = time.perf_counter()
    registry = check.registry
    domain_hits, phone_hits, unknown = [], [], []
    for host in hosts:
        if host in skip or contacts.is_freemail(host):
            continue
        if agency and agencies.is_official_host(agency, host):
            domain_hits.append(host)
        elif not contacts.is_government(host) and not any(
                contacts.on_domain(host, d) for d in agencies.all_domains(registry)):
            unknown.append(host)
    for phone in phones:
        if agency and agencies.is_official_phone(agency, phone):
            phone_hits.append(phone)
        elif not any(agencies.is_official_phone(a, phone) for a in registry["agencies"]):
            unknown.append(phone)
    official = domain_hits + phone_hits + [p for p in short_official if p not in phone_hits]

    step = "rule:unknown_contact"
    if not agency:
        if unknown:
            first = unknown[0]
            idx = check.text.lower().find(first.lower())
            check.flag("unknown_contact", quote=snippet(check.text, idx, idx + len(first)) if idx >= 0 else first,
                       grounded=check.code_grounded(idx), severity="info")
            check.add_trace(step, "unknown", f"{len(unknown)} contact(s) could not be checked: the sender is not "
                                             f"in our registry", started)
        else:
            check.add_trace(step, "unknown", "No agency to compare contacts against", started)
        return official
    if unknown:
        first = unknown[0]
        idx = check.text.lower().find(first.lower())
        official_line = (agency.get("phones") or [{}])[0].get("number") or agency.get("official_site")
        listed = ", ".join(unknown[:3]) + (" and more" if len(unknown) > 3 else "")
        check.flag("unknown_contact", quote=snippet(check.text, idx, idx + len(first)) if idx >= 0 else first,
                   grounded=check.code_grounded(idx), severity="medium",
                   why=f"{listed} {'is' if len(unknown) == 1 else 'are'} not on {agency['name']}'s official "
                       f"contact list (checked {agency.get('checked_on')}). Use {official_line} instead.")
        check.add_trace(step, "flag", f"Official: {', '.join(official) or 'none'}. Not official: {listed}", started)
    elif official:
        check.add_trace(step, "pass", f"Every contact matches {agency['name']}'s official list: "
                                      f"{', '.join(official)}", started)
    else:
        check.add_trace(step, "unknown", "The letter gives no phone number, link or email to compare", started)
    return official


def _rule_injection_model(check):
    started = time.perf_counter()
    items = check.ex["ai_instructions"]
    if not items:
        check.add_trace("rule:injection_detected_model", "pass", "The model reported no instructions aimed at AI",
                        started)
        return
    _quote, ok = check.model_quote(items)
    check.flag("injection_detected_model", quote=None, grounded=ok, redacted=True)
    check.add_trace("rule:injection_detected_model", "flag", "The model reported text addressed to AI tools "
                                                             "(redacted)", started)


# ---------------------------------------------------------------- dates and amounts

def _letter_date(check):
    quote = check.ex["letter_date"]["quote"]
    if quote and check.ground(quote) is not False:
        parsed = dates.parse_date(quote, check.country)
        if parsed:
            return parsed, "quoted from the letter"
    parsed, _raw = dates.find_letter_date(check.text, check.country)
    if parsed:
        return parsed, "found in the letter text"
    if not check.independent and check.ex["letter_date"]["value"]:
        parsed = dates.parse_date(check.ex["letter_date"]["value"], check.country)
        if parsed:
            return parsed, "read by the model only, not independently grounded"
    return None, None


def _relative_deadline(check, n, business, anchor, letter_date):
    if anchor == "receipt":
        return dates.add_days(check.today, n, business), \
            f"date received (taken as {check.today.isoformat()}) + {n} {'business ' if business else ''}days"
    if letter_date:
        return dates.add_days(letter_date, n, business), f"letter_date + {n} {'business ' if business else ''}days"
    return None, None


def _deadlines(check, letter_date):
    found = {}

    def keep(value, what, quote, computed_from):
        if letter_date and not (letter_date - timedelta(days=1) <= value <= letter_date + timedelta(days=1100)):
            return
        key = value.isoformat()
        if key not in found or (what and found[key]["what"] == "Deadline in the letter"):
            found[key] = {"date": key, "what": what or "Deadline in the letter", "quote": quote,
                          "computed_from": computed_from}

    for item in check.ex["deadlines"]:
        quote = item["quote"]
        if not quote or check.ground(quote) is False:
            continue  # never turn an ungrounded quote into a calendar entry
        value = dates.parse_date(quote, check.country)
        computed = None
        if value is None:
            rel = next((r for r in dates.relative_mentions(quote) if r["unit"] == "days"), None)
            if rel:
                value, computed = _relative_deadline(check, rel["n"], rel["business"], rel["anchor"], letter_date)
            elif item["relative_days"] and str(item["relative_days"]) in quote:
                anchor = "receipt" if item["relative_to"] == "receipt" else "letter_date"
                value, computed = _relative_deadline(check, item["relative_days"], False, anchor, letter_date)
        if value is None and not check.independent and item["absolute_date"]:
            value = dates.parse_date(item["absolute_date"], check.country)
            computed = "read by the model only, not independently grounded" if value else None
        if value:
            keep(value, item["what"], quote, computed)

    text = check.text
    for value, start, end, _raw in dates.deadline_dates(text, check.country):
        keep(value, "", snippet(text, start, end), None)
    for rel in dates.relative_mentions(text):
        if rel["unit"] != "days":
            continue
        value, computed = _relative_deadline(check, rel["n"], rel["business"], rel["anchor"], letter_date)
        if value:
            keep(value, "", snippet(text, rel["start"], rel["end"]), computed)
    return sorted(found.values(), key=lambda d: d["date"])


def _redact_deadline(deadline):
    if deadline["quote"] and lexicon.AI_INSTRUCTION.search(deadline["quote"]):
        return {**deadline, "quote": None}
    return deadline


def _amounts(check):
    found = [m.group().strip() for m in lexicon.AMOUNT.finditer(check.text)]
    for item in check.ex["amounts"]:
        amount = item.get("amount") or ""
        if amount and item.get("quote") and check.ground(item["quote"]) is not False \
                and lexicon.AMOUNT.search(amount):
            found.append(amount)
    return _unique(found, key=lambda a: re.sub(r"[^\d.]", "", a))[:10]


# ---------------------------------------------------------------- redaction and verdict

def _redact(text, ex):
    """Drop lines addressed to AI tools before the text is returned or passed to the explainer."""
    model_quotes = [i["quote"] for i in ex["ai_instructions"] if len(i.get("quote") or "") >= 12][:MAX_QUOTES_PER_RULE]
    lines = []
    for line in text.splitlines():
        hit = lexicon.AI_INSTRUCTION.search(line) or any(
            grounding.is_grounded(q, line) for q in model_quotes if len(line) >= len(q) * 0.5)
        lines.append("[instruction aimed at AI tools removed]" if hit else line)
    return "\n".join(lines)


def _verdict(check, agency, official_hits):
    started = time.perf_counter()
    score = sum(POINTS[f["severity"]] for f in check.flags)
    strong = sum(f["severity"] == "strong" for f in check.flags)
    medium = sum(f["severity"] == "medium" for f in check.flags)
    ai_flagged = any(f["rule"] in ("ai_instruction", "injection_detected_model") for f in check.flags)
    grounding_ok = check.independent and not check.partial and (
        check.checked == 0 or check.grounded / check.checked >= GROUNDED_SHARE_FOR_GENUINE)
    name = agency["name"] if agency else None
    phone = ((agency or {}).get("phones") or [{}])[0].get("number") if agency else None

    if score >= SCAM_SCORE:
        verdict = "likely_scam"
        top = check.flags[0]["title"]
        headline = f"This looks like a scam: it {top[0].lower()}{top[1:].rstrip('.')}."
        if name:
            headline += " Do not use the contact details in it."
            if phone:
                headline += f" {name}'s official line is {phone}."
        reason = "score of 3 or more"
    elif agency and official_hits and score == 0 and grounding_ok and not ai_flagged:
        verdict = "consistent_with_genuine"
        headline = (f"Nothing in this letter contradicts a genuine {name} letter, and its contact details match the "
                    f"official ones. Still, confirm by calling {phone or 'the official number'} yourself.")
        reason = "agency matched, official contact found, no warning signs, quotes grounded"
    else:
        verdict = "cant_tell"
        reason = _cant_tell_reason(check, agency, official_hits, score, grounding_ok)
        if not agency:
            headline = ("We couldn't match the sender to an agency we hold official contacts for, so we can't vouch "
                        "for it. Contact the sender using details you find yourself, not the ones in the letter.")
        elif score:
            headline = (f"Some details don't fit a genuine {name} letter. Check with {name} directly"
                        f"{' on ' + phone if phone else ''}, not with the contacts in the letter.")
        else:
            headline = (f"We couldn't confirm this against {name}'s official contacts. Check with {name} directly"
                        f"{' on ' + phone if phone else ''}.")
    label = verdict_label(verdict, name)
    check.add_trace("verdict", "done", f"Score {score} ({strong} strong x3, {medium} medium x1): {label}. "
                                       f"Reason: {reason}.", started)
    return {"verdict": verdict, "verdict_label": label, "headline": headline}


def verdict_label(verdict, agency_name=None):
    if verdict == "likely_scam":
        return "Likely scam"
    if verdict == "consistent_with_genuine":
        who = f"{agency_name} " if agency_name else ""
        return f"Consistent with a genuine {who}letter — confirm on the official number"
    return "Can't tell"


def _cant_tell_reason(check, agency, official_hits, score, grounding_ok):
    if not agency:
        return "sender not in the registry"
    if score:
        return f"warning signs worth {score} point(s), below the scam threshold of {SCAM_SCORE}"
    if not official_hits:
        return "no official phone number or domain in the letter"
    if not grounding_ok and check.partial:
        return "part of the letter could only be read by the AI model, so it can't be confirmed as genuine"
    if not grounding_ok:
        return "the letter could not be independently read, so quotes are not grounded"
    return "text addressed to AI tools was reported"
