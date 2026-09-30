"""Date parsing and deadline arithmetic. The model never does date math; this module does."""
import re
from datetime import date, timedelta

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4, "april": 4, "may": 5,
    "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}
_MONTH = r"(?P<mon>" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + r")\.?"
_ORD = r"(?:st|nd|rd|th)?"

_DATE_PATTERNS = [
    re.compile(r"(?<!\d)(?P<y>\d{4})-(?P<m>\d{1,2})-(?P<d>\d{1,2})(?!\d)"),
    re.compile(_MONTH + r"\s+(?P<d>\d{1,2})" + _ORD + r",?\s+(?P<y>\d{4})(?!\d)", re.I),
    re.compile(r"(?<!\d)(?P<d>\d{1,2})" + _ORD + r"(?:\s+of)?[\s-]+" + _MONTH + r"[\s,-]+(?P<y>\d{4}|\d{2})(?!\d)",
               re.I),
    re.compile(r"(?<![\d/.-])(?P<a>\d{1,2})[/.-](?P<b>\d{1,2})[/.-](?P<y>\d{4}|\d{2})(?![\d/.-])"),
]

_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "fourteen": 14, "fifteen": 15, "twenty": 20, "twenty-one": 21, "thirty": 30, "forty-five": 45, "sixty": 60,
    "ninety": 90,
}
RELATIVE_RE = re.compile(
    r"\b(?:within|in|no later than|not later than|not more than)\s+"
    r"(?P<n>\d{1,3}|" + "|".join(sorted(_WORD_NUMBERS, key=len, reverse=True)) + r")(?:\s*\(\d{1,3}\))?\s+"
    r"(?P<kind>calendar\s+|working\s+|business\s+)?(?P<unit>days?|hours?|hrs?)\b(?P<tail>[^.\n]{0,70})",
    re.I,
)
RELATIVE_HI_RE = re.compile(r"(?P<n>\d{1,3})\s*(?P<unit>दिनों|दिन|घंटे|घंटों)\s*(?:के\s*)?(?:भीतर|अंदर|में)")
_RECEIPT = re.compile(r"receipt|receiv|प्राप्ति", re.I)
_DEADLINE_CUE = re.compile(
    r"(?:\b(?:pay(?:ment)?|respond|reply|due(?: date)?|payable|deadline|last date|expire[sd]?|expiry)"
    r"\W{0,3}(?:\w+\W+){0,3}"
    r"|\b(?:by|before|no later than|not later than|on or before|until|till)\W{1,3}|अंतिम तिथि\W{0,3})$",
    re.I,
)
_LETTER_DATE_LABEL = re.compile(
    r"(?:notice date|letter date|date of (?:notice|issue|letter)|issue date|issued on|dated|date|दिनांक|तारीख)"
    r"\s*[:.\-]?\s*$",
    re.I,
)


def _year(y):
    y = int(y)
    return 2000 + y if y < 100 else y


def _build(y, m, d):
    try:
        result = date(_year(y), int(m), int(d))
    except ValueError:
        return None
    return result if 2000 <= result.year <= 2100 else None


def find_dates(text, country=None):
    """All dates in text as (date, start, end, raw), in reading order, without overlaps."""
    hits = []
    for pattern in _DATE_PATTERNS:
        for m in pattern.finditer(text or ""):
            g = m.groupdict()
            if g.get("mon"):
                value = _build(g["y"], _MONTHS[g["mon"].lower().rstrip(".")], g["d"])
            elif g.get("a"):
                a, b = int(g["a"]), int(g["b"])
                month_first = (country == "US" and a <= 12) or b > 12
                value = _build(g["y"], a, b) if month_first else _build(g["y"], b, a)
            else:
                value = _build(g["y"], g["m"], g["d"])
            if value:
                hits.append((value, m.start(), m.end(), m.group()))
    hits.sort(key=lambda h: (h[1], -(h[2] - h[1])))
    result, last_end = [], -1
    for h in hits:
        if h[1] >= last_end:
            result.append(h)
            last_end = h[2]
    return result


def parse_date(text, country=None):
    """First date in a string (an ISO value or a quote), or None."""
    found = find_dates(text or "", country)
    return found[0][0] if found else None


def find_letter_date(text, country=None):
    """Date printed as the letter's own date: labelled ("Date: ...") first, else the first date in the header
    that is not phrased as a deadline. Returns (date, raw) or (None, None)."""
    dates = find_dates(text, country)
    for value, start, _end, raw in dates:
        if _LETTER_DATE_LABEL.search(text[max(0, start - 25):start]):
            return value, raw
    header_end = _nth_line_end(text, 12)
    for value, start, _end, raw in dates:
        if start > header_end:
            break
        if not _DEADLINE_CUE.search(text[max(0, start - 40):start]):
            return value, raw
    return None, None


def _nth_line_end(text, n):
    pos = -1
    for _ in range(n):
        pos = text.find("\n", pos + 1)
        if pos == -1:
            return len(text)
    return pos


def add_days(start, n, business=False):
    if not business:
        return start + timedelta(days=n)
    current, added = start, 0
    while added < n:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def word_number(token):
    token = token.lower()
    return int(token) if token.isdigit() else _WORD_NUMBERS.get(token)


def relative_mentions(text):
    """'within 30 days of this notice' style phrases -> list of dicts with n, unit, business, anchor, span."""
    found = []
    for m in RELATIVE_RE.finditer(text or ""):
        n = word_number(m.group("n"))
        if n is None:
            continue
        unit = "hours" if m.group("unit").lower().startswith("h") else "days"
        anchor = "receipt" if _RECEIPT.search(m.group("tail")) else "letter_date"
        found.append({"n": n, "unit": unit, "business": bool(m.group("kind") and "calendar" not in m.group("kind").lower()),
                      "anchor": anchor, "start": m.start(), "end": m.end()})
    for m in RELATIVE_HI_RE.finditer(text or ""):
        unit = "hours" if "घंट" in m.group("unit") else "days"
        found.append({"n": int(m.group("n")), "unit": unit, "business": False, "anchor": "letter_date",
                      "start": m.start(), "end": m.end()})
    return found


def deadline_dates(text, country=None):
    """Absolute dates phrased as deadlines ("pay by October 21, 2026") -> list of (date, start, end, raw)."""
    return [d for d in find_dates(text, country) if _DEADLINE_CUE.search(text[max(0, d[1] - 40):d[1]])]
