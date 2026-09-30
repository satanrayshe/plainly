"""Official-contacts registry: loading, agency matching and contact checks.

Matching order follows the contract: the letter's own claim (name/alias) first, then registry domains, then phones.
"""
import json
import os
import re
from functools import lru_cache
from pathlib import Path

import contacts

HERE = Path(__file__).resolve().parent
DEFAULT_PATH = HERE / "registry.json"
FIXTURE_PATH = HERE / "tests" / "fixtures" / "registry_test.json"


def registry_path():
    configured = os.environ.get("REGISTRY_PATH")
    if configured:
        return Path(configured)
    if not DEFAULT_PATH.exists() and os.environ.get("PLAINLY_MOCK") == "1" and FIXTURE_PATH.exists():
        return FIXTURE_PATH  # offline UI work before the real registry lands
    return DEFAULT_PATH


@lru_cache(maxsize=4)
def _load(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("agencies", [])
    data.setdefault("report_channels", {})
    return data


def load_registry(path=None):
    return _load(str(path or registry_path()))


def _alias_pattern(alias):
    alias = alias.strip()
    body = re.escape(alias).replace(r"\ ", r"\s+")
    if len(alias) <= 5 and alias.isupper():
        return re.compile(rf"(?<![A-Za-z]){body}(?![A-Za-z])")  # acronyms: case-sensitive
    return re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE)


# "your Social Security number" or "Aadhaar card" names an ID document, not the sender.
_ID_DOCUMENT_AFTER = re.compile(r"\s*(?:numbers?|no\b|nos\b|#|cards?|linked|details|holders?|seeded)", re.IGNORECASE)


def _alias_hits(agency, text):
    hits = []
    text = text or ""
    for alias in [agency.get("name", "")] + list(agency.get("aliases", [])):
        if not alias or not alias.strip():
            continue
        for m in _alias_pattern(alias).finditer(text):
            if not _ID_DOCUMENT_AFTER.match(text, m.end()):
                hits.append((m.start(), alias))
                break
    return hits


def by_key(registry, key):
    return next((a for a in registry["agencies"] if a.get("key") == key), None)


def match_agency(registry, *, claimed_key=None, claimed_sender="", text="", hosts=(), phones=(),
                 trust_model_key=False):
    """-> (agency or None, human-readable reason)."""
    candidate = by_key(registry, claimed_key) if claimed_key else None
    if candidate and (_alias_hits(candidate, f"{claimed_sender}\n{text}") or trust_model_key):
        return candidate, f"the letter names {candidate['name']}"

    best, best_score = None, 0
    for agency in registry["agencies"]:
        in_sender = bool(_alias_hits(agency, claimed_sender))
        in_text = _alias_hits(agency, text)
        score = (10 if in_sender else 0) + len(in_text)
        if in_text:
            score += 1 / (1 + min(pos for pos, _ in in_text))  # earlier mention breaks ties
        if score > best_score:
            best, best_score = agency, score
    if best:
        return best, f"the letter names {best['name']}"

    for agency in registry["agencies"]:
        if any(contacts.on_domain(h, d) for h in hosts for d in agency.get("domains", [])):
            return agency, f"a link or email is on {agency['name']}'s official domain"
    for agency in registry["agencies"]:
        if any(contacts.same_phone(p, o["number"]) for p in phones for o in agency.get("phones", [])):
            return agency, f"a phone number matches {agency['name']}'s official list"
    return None, "no agency in our registry is named in the letter"


def official_phone_hits(agency, phones, text):
    """Official numbers for this agency that appear in the letter (long numbers by key, short ones by context)."""
    hits = []
    for official in agency.get("phones", []):
        number = official["number"]
        if len(re.sub(r"\D", "", number)) < 8:
            if contacts.find_short_number(text, number):
                hits.append(number)
        elif any(contacts.same_phone(p, number) for p in phones):
            hits.append(number)
    return hits


def is_official_phone(agency, phone):
    return any(contacts.same_phone(phone, o["number"]) for o in agency.get("phones", []))


def is_official_host(agency, host):
    return any(contacts.on_domain(host, d) for d in agency.get("domains", []))


def all_domains(registry):
    return [d for a in registry["agencies"] for d in a.get("domains", [])]


def brand_words(registry):
    """Single-word acronyms and names (IRS, HMRC, UIDAI...) that scammers stuff into their own domains,
    mapped to the agency's first official domain."""
    words = {}
    for agency in registry["agencies"]:
        official = (agency.get("domains") or [contacts.host_of(agency.get("official_site", ""))])[0]
        for alias in agency.get("aliases", []) + [agency.get("key", "")]:
            alias = (alias or "").strip()
            if re.fullmatch(r"[A-Za-z]{3,12}", alias):
                words.setdefault(alias.lower(), official)
    return words


def report_channel(registry, country):
    return registry["report_channels"].get((country or "").upper())


def public_view(registry, agency):
    """Agency block for the API response."""
    phones = agency.get("phones", [])
    return {
        "key": agency["key"],
        "name": agency["name"],
        "country": agency.get("country"),
        "official_phone": phones[0]["number"] if phones else None,
        "official_site": agency.get("official_site"),
        "report_channel": report_channel(registry, agency.get("country")),
        "source_url": agency.get("source_url"),
        "checked_on": agency.get("checked_on"),
    }
