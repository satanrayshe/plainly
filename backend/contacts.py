"""Phones, links and email addresses: extraction from letter text, normalization and domain tests.

Everything here is plain regex and string work so it runs identically in Lambda, tests and the dev server.
"""
import re
import unicodedata

# Second-level suffixes that behave like TLDs, so "incometax.gov.in" has registrable label "incometax".
MULTI_SUFFIXES = {
    "gov.in", "nic.in", "bank.in", "co.in", "org.in", "net.in", "ac.in", "edu.in", "res.in", "firm.in", "gen.in", "ind.in",
    "gov.uk", "co.uk", "org.uk", "ac.uk", "nhs.uk", "police.uk", "ltd.uk", "plc.uk", "me.uk",
    "com.au", "gov.au", "co.nz", "com.sg", "com.br", "co.za",
}
# Registrations under these are restricted to government bodies, so they are never a lookalike and never
# an "unknown" contact in the scam sense.
GOVERNMENT_SUFFIXES = ("gov", "mil", "gov.in", "nic.in", "gov.uk", "police.uk", "nhs.uk")

FREEMAIL = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.in", "yahoo.co.uk", "ymail.com", "rocketmail.com",
    "outlook.com", "hotmail.com", "hotmail.co.uk", "live.com", "msn.com", "aol.com", "icloud.com", "me.com",
    "protonmail.com", "proton.me", "pm.me", "rediffmail.com", "rediff.com", "zohomail.in", "zohomail.com",
    "mail.com", "gmx.com", "gmx.net", "yandex.com", "tutanota.com", "tuta.io",
}

# Common TLDs for bare "example.com" mentions without a scheme. Kept explicit to avoid "Mr.Smith" style hits.
_TLDS = (
    "com|net|org|info|biz|gov|mil|edu|in|uk|us|co|io|me|ai|app|xyz|top|online|site|live|shop|club|vip|cc|tk|ml|"
    "ga|cf|gq|icu|cn|ru|pw|link|click|support|help|services|pro|ly|to|ws|tv|website|space|store|tech|fun|"
    "today|world|cloud|digital|email|global|page|win|bid|loan|work|review|country|stream|download|zip|mov|li|gy|gd"
)
URL_RE = re.compile(
    r"(?:https?://|\bwww\.)[^\s<>\"'()\[\]{}]+"
    r"|(?<![@\w.-])(?:[^\W_][\w-]*\.)+(?:" + _TLDS + r")\b(?![@.-]?\w*@)(?:/[^\s<>\"'()\[\]{}]*)?",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@((?:[^\W_][\w-]*\.)+[^\W\d_]{2,})(?![\w-])")
# UPI virtual payment addresses: handle@bank with no dot after the provider (e.g. ravi.k@okaxis, 98xxxxxx@ybl).
UPI_RE = re.compile(r"(?<![\w.+-])[\w.-]{2,}@[a-zA-Z][a-zA-Z0-9]{1,19}(?![\w@-]|\.\w)")

_PHONE_CANDIDATE = re.compile(r"(?<![\w+(])(?:\+|00)?\(?\d[\d \t().-]{5,20}\d(?!\w)")
_DATE_SHAPE = re.compile(r"\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}")
_AADHAAR_SHAPE = re.compile(r"\d{4} \d{4} \d{4}")
_ZIP4_SHAPE = re.compile(r"\d{5}-\d{4}")
_NOT_PHONE_CONTEXT = re.compile(
    r"(account|a/c|acct|consumer|customer id|ca no|k\.? ?no|case|ref|reference|notice|invoice|bill no|policy|"
    r"aadhaar|aadhar|\bpan\b|ssn|social security|\bid\b|serial|order|tracking|awb|challan|receipt|txn|utr|"
    r"amount|rs\.?|inr|₹|\$|£)[^\n]{0,18}$",
    re.IGNORECASE,
)
_PHONE_CONTEXT = re.compile(
    r"(call|phone|tel|telephone|helpline|toll|whatsapp|contact|mob|mobile|ph\b|dial|sms|text|ring|"
    r"फोन|मोबाइल|कॉल|हेल्पलाइन|संपर्क)",
    re.IGNORECASE,
)

# Link shorteners hide where a link goes. Matched on the whole host; the labels catch "tinyurl.co" style variants.
SHORTENERS = {
    "bit.ly", "bitly.com", "tinyurl.com", "goo.gl", "ow.ly", "is.gd", "v.gd", "buff.ly", "rb.gy", "cutt.ly",
    "shorturl.at", "short.gy", "surl.li", "tiny.cc", "t.ly", "s.id", "rebrand.ly", "shorte.st", "bl.ink", "x.gd",
    "t2m.io", "tiny.one", "u.to", "shrtco.de", "qrco.de", "urlz.fr", "clck.ru", "inx.lv", "1url.com", "lnkd.in",
}
_SHORTENER_LABELS = {"bitly", "tinyurl", "cutt", "shorturl", "rebrand", "shorte"}
# Free website builders and app hosts: anyone can put up a page here in minutes, under any name.
FREE_HOSTS = (
    "vercel.app", "netlify.app", "web.app", "firebaseapp.com", "github.io", "pages.dev", "workers.dev",
    "herokuapp.com", "glitch.me", "onrender.com", "weebly.com", "wixsite.com", "blogspot.com", "000webhostapp.com",
    "ngrok.io", "ngrok-free.app", "repl.co", "godaddysites.com", "webflow.io", "framer.website", "square.site",
)
# Links that open a chat with a person rather than an organisation's website.
CHAT_LINKS = ("wa.me", "api.whatsapp.com", "chat.whatsapp.com", "t.me", "telegram.me")
# Government bulk mailers that send on an agency's behalf (IRS and many US agencies use GovDelivery).
GOVERNMENT_MAILERS = ("govdelivery.com",)

_CONFUSABLES = str.maketrans({
    "0": "o", "1": "l", "i": "l", "|": "l", "3": "e", "5": "s", "$": "s", "7": "t", "@": "a", "4": "a",
    # Cyrillic and Greek letters that render like Latin ones
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "l", "ј": "j", "ѕ": "s",
    "ԁ": "d", "ɡ": "g", "һ": "h", "ո": "n", "ν": "v", "ο": "o", "α": "a", "ι": "l", "κ": "k", "τ": "t",
})


# ---------------------------------------------------------------- phones

def phone_key(raw):
    """Canonical national number for comparison: +1 / +91 / +44 / 00 / trunk 0 / US leading 1 removed."""
    raw = (raw or "").strip()
    digits = re.sub(r"\D", "", raw)
    international = raw.startswith("+") or digits.startswith("00")
    if digits.startswith("00"):
        digits = digits[2:]
    if international or len(digits) > 10:
        for code in ("91", "44", "1"):
            if digits.startswith(code) and len(digits) - len(code) in (9, 10):
                digits = digits[len(code):]
                break
    if digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]  # 1-800-... written without "+"; applied to both sides so comparisons stay fair
    return digits


def same_phone(a, b):
    ka, kb = phone_key(a), phone_key(b)
    if not ka or not kb:
        return False
    return ka == kb or (len(ka) >= 10 and len(kb) >= 10 and ka[-10:] == kb[-10:])


def find_phones(text):
    """Phone-shaped numbers with their character span, skipping dates, amounts and ID numbers."""
    found = []
    for m in _PHONE_CANDIDATE.finditer(text or ""):
        raw = m.group()
        if raw.count("(") > raw.count(")"):
            raw = raw[:raw.rfind("(")]  # "+91-80-46122000 (08:00 hrs)": the opening hours are not part of it
        cand = raw.strip(" \t.-")
        digits = re.sub(r"\D", "", cand)
        if not 8 <= len(digits) <= (15 if cand.startswith("+") else 13):
            continue
        if _DATE_SHAPE.fullmatch(cand) or _AADHAAR_SHAPE.fullmatch(cand) or _ZIP4_SHAPE.fullmatch(cand):
            continue
        if len(set(digits.lstrip("0"))) <= 1 or _is_scan_line(text, m.start()):
            continue  # placeholders like 0000000 0000, and OCR scan lines full of digits
        before = text[max(0, m.start() - 40):m.start()]
        if _NOT_PHONE_CONTEXT.search(before) and not _PHONE_CONTEXT.search(before[-20:]):
            continue
        if re.search(r"\b[A-Z]{2},?\s{1,2}$", before) and len(digits) <= 9:
            continue  # "CINCINNATI, OH 45999-0149": a ZIP code in an address line
        start = m.start() + raw.find(cand)
        found.append((cand, start, start + len(cand)))
    return found


def _is_scan_line(text, pos):
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    line = text[start:len(text) if end == -1 else end]
    return bool(re.fullmatch(r"[\d\s]+", line)) and sum(c.isdigit() for c in line) > 15


def plausible_for_country(phone, country):
    """US letters: drop numbers that cannot be North American (area and exchange codes start 2-9)."""
    if country != "US":
        return True
    key = phone_key(phone)
    return len(key) != 10 or (key[0] in "23456789" and key[3] in "23456789")


def find_short_number(text, number):
    """Short helplines (1930, 1947, 19123) only count when phone words sit nearby."""
    digits = re.sub(r"\D", "", number)
    for m in re.finditer(rf"(?<!\d){re.escape(digits)}(?!\d)", text or ""):
        window = text[max(0, m.start() - 40):m.end() + 20]
        if _PHONE_CONTEXT.search(window):
            return m
    return None


# ---------------------------------------------------------------- links and emails

def host_of(url_or_host):
    s = (url_or_host or "").strip().lower()
    s = re.sub(r"^[a-z][a-z0-9+.-]*://", "", s)
    s = s.split("/")[0].split("?")[0].split("#")[0].split("@")[-1].split(":")[0]
    s = s.strip(".")
    return s[4:] if s.startswith("www.") else s


def find_urls(text):
    urls = []
    for m in URL_RE.finditer(text or ""):
        url = m.group().rstrip(".,;:!?'\"")
        host = host_of(url)
        if "." not in host:
            continue
        tld = url.split("/")[0].rsplit(".", 1)[-1]
        if not re.match(r"(?i)https?://|www\.", url) and tld[:1].isupper() and tld[1:].islower():
            continue  # "Pay now.In case" is a missing space, not a web address
        urls.append((url, m.start(), m.start() + len(url)))
    return urls


def find_emails(text):
    return [(m.group(), m.start(), m.end()) for m in EMAIL_RE.finditer(text or "")]


def find_upi_ids(text):
    return [(m.group(), m.start(), m.end()) for m in UPI_RE.finditer(text or "")]


def split_host(host):
    """-> (registrable label, suffix), e.g. "pay.irs-gov.com" -> ("irs-gov", "com")."""
    parts = host_of(host).split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in MULTI_SUFFIXES:
        return parts[-3], ".".join(parts[-2:])
    if len(parts) >= 2:
        if ".".join(parts[-2:]) in MULTI_SUFFIXES:
            return "", ".".join(parts[-2:])  # the host *is* a suffix, e.g. gov.uk
        return parts[-2], parts[-1]
    return parts[0], ""


def on_domain(host, domain):
    host, domain = host_of(host), host_of(domain)
    return bool(domain) and (host == domain or host.endswith("." + domain))


def is_government(host):
    host = host_of(host)
    return any(host == s or host.endswith("." + s) for s in GOVERNMENT_SUFFIXES)


# Registrations restricted to vetted banks, so a link there is the bank's own site: .bank.in is open only to
# RBI-regulated banks (RBI Statement on Developmental and Regulatory Policies, 7 February 2025; registrar IDRBT),
# and .sbi is State Bank of India's own top-level domain. hdfcbank.com now redirects to hdfc.bank.in.
RESTRICTED_BANK_SUFFIXES = ("bank.in", "sbi")


def is_restricted_bank(host):
    host = host_of(host)
    return any(host.endswith("." + s) for s in RESTRICTED_BANK_SUFFIXES)


def is_freemail(domain):
    domain = host_of(domain)
    return domain in FREEMAIL or any(domain.endswith("." + f) for f in FREEMAIL)


# ---------------------------------------------------------------- lookalikes

def skeleton(label):
    """Map visually confusable characters to one form so "1rs", "іrs" (Cyrillic) and "irs" collide."""
    s = unicodedata.normalize("NFKC", label).lower()
    s = s.replace("rn", "m").replace("vv", "w").replace("cl", "d")
    return s.translate(_CONFUSABLES)


def decode_punycode(host):
    labels = []
    for label in host_of(host).split("."):
        if label.startswith("xn--"):
            try:
                label = label.encode("ascii").decode("idna")
            except (UnicodeError, ValueError):
                pass
        labels.append(label)
    return ".".join(labels)


def levenshtein(a, b, cap=3):
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def near_miss(candidate, brand):
    """One or two typos away from a brand. Short brands (4-6 letters) only allow a swapped or substituted
    letter, so "ups" is not a near miss of "usps" and "train" is not one of "trai"."""
    if candidate == brand or len(brand) < 4:
        return False
    if len(brand) >= 7:
        return levenshtein(candidate, brand) <= 2
    if len(candidate) != len(brand):
        return False
    diffs = [i for i, (x, y) in enumerate(zip(candidate, brand)) if x != y]
    if len(diffs) == 1:
        return True
    return len(diffs) == 2 and diffs[1] == diffs[0] + 1 and candidate[diffs[0]] == brand[diffs[1]]         and candidate[diffs[1]] == brand[diffs[0]]


_BRAND_PADDING = {"gov", "govt", "official", "online", "help", "support", "refund", "refunds", "secure", "verify",
                  "portal", "service", "services", "pay", "payment", "payments", "india", "in", "uk", "us", "usa",
                  "login", "update", "claim", "tax", "care", "desk", "team", "info", "notice", "alert"}


def lookalike_reason(host, brand_domains, brand_words):
    """Why `host` imitates one of the official domains, or None.

    brand_domains: official domains (e.g. "irs.gov", "incometax.gov.in")
    brand_words:   short brand tokens (e.g. "irs", "hmrc") used for "brand inside someone else's domain" checks
    """
    host = host_of(host)
    if not host or is_government(host) or is_freemail(host):
        return None
    if any(on_domain(host, d) for d in brand_domains):
        return None
    decoded = decode_punycode(host)
    punycode = decoded != host
    label, _suffix = split_host(decoded)
    brands = {}
    for d in brand_domains:
        b_label, _ = split_host(d)
        if b_label and len(b_label) >= 3:
            brands.setdefault(b_label, d)
    words = brand_words if isinstance(brand_words, dict) else {w: w for w in brand_words}
    for word, official in words.items():
        if len(word) >= 3:
            brands.setdefault(word.lower(), official)

    for brand, official in brands.items():
        if label == brand:
            return f"uses the name '{brand}' on a different ending than the official {official}"
        if skeleton(label) == skeleton(brand):
            how = "punycode (xn--) characters" if punycode else "look-alike characters"
            return f"imitates {official} using {how}"
        if near_miss(label, brand):
            return f"is one or two letters away from {official}"
    # The brand hidden elsewhere in the name: irs.gov.refund-center.com, irsgov.com, 1rs.gov-pay.net
    tokens = [t for t in re.split(r"[.\-_]", decoded) if len(t) >= 3]
    for brand, official in brands.items():
        for t in tokens:
            padded = (t.startswith(brand) and t[len(brand):] in _BRAND_PADDING) \
                or (t.endswith(brand) and t[:-len(brand)] in _BRAND_PADDING)
            close = skeleton(t) == skeleton(brand) or near_miss(t, brand)
            if t == brand or padded or close:
                return f"puts '{brand}' inside an address that is not {official}"
    if punycode:
        return "uses punycode (xn--) characters that can disguise a web address"
    return None


# ---------------------------------------------------------------- risky links and personal numbers

def risky_link_reason(url_or_host):
    """Why a link hides its real destination or owner, or None: shortener, raw IP address, free web host."""
    host = host_of(url_or_host)
    if not host:
        return None
    if any(on_domain(host, d) for d in SHORTENERS) or split_host(host)[0] in _SHORTENER_LABELS:
        return "is a link shortener, which hides where the link really goes"
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", host):
        return "is a bare internet (IP) address, not an organisation's website"
    if any(on_domain(host, f) for f in FREE_HOSTS):
        return "is on a free website host where anyone can put up a page under any name"
    return None


def is_chat_link(url_or_host):
    host = host_of(url_or_host)
    return any(on_domain(host, c) for c in CHAT_LINKS)


def is_personal_mobile(phone, country=""):
    """An Indian (6-9xxxx xxxxx) or UK (07...) mobile number: a person's phone, not an office line.

    A bare 10-digit number is only read as Indian when the letter is Indian, or its country is unknown and the
    number is not written the US way, (801) 317-8874 or 801-317-8874.
    """
    raw = (phone or "").strip()
    digits = re.sub(r"\D", "", raw)
    if country in ("", "UK") and re.fullmatch(r"(?:44|0)7\d{9}", digits):
        return True
    if re.fullmatch(r"91[6-9]\d{9}", digits):
        return True
    if not re.fullmatch(r"[6-9]\d{9}", digits) and not re.fullmatch(r"0[6-9]\d{9}", raw):
        return False  # 0824-060-6707 is a landline with an area code; a mobile with a 0 is written 09810012345
    if raw.startswith("+"):
        return False
    us_style = "(" in raw or re.fullmatch(r"\d{3}[-.\s]\d{3}[-.\s]\d{4}", raw)
    return country == "IN" or (country == "" and not us_style)
