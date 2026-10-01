"""Build the static site: site/ + samples/ -> dist/.

- copies site/ (minus _partials/) into dist/
- fills the shared <!-- @head -->, <!-- @header -->, <!-- @footer --> markers
- pre-renders the landing sample cards and the /try/ sample tiles from samples/results/<id>.json (the live
  run), falling back to samples/results/mock/<id>.json (the offline run), so the examples read without JavaScript
- copies sample results (with letter_text removed) and letter images into dist/samples/

Usage:
  python scripts/build_site.py [--out dist] [--site-url https://example.cloudfront.net] [--strict]

--site-url (or env SITE_URL) makes og:url / og:image absolute.
--strict fails the build when a landing sample result is missing, or any sample result is still mock data.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
SAMPLES = ROOT / "samples"
PARTIALS = SITE / "_partials"

# Order matters: landing shows the first three flagged landing=True, /try/ shows all.
CATALOG = [
    {"id": "electricity-final-notice", "title": "Electricity “final notice”",
     "kind": "Letter threatening to cut the power tonight", "landing": True},
    {"id": "irs-balance-due", "title": "IRS balance-due notice",
     "kind": "U.S. tax notice asking for payment, in the genuine format", "landing": True},
    {"id": "digital-arrest-parcel", "title": "“CBI” arrest warrant over a parcel",
     "kind": "Customs parcel and “digital arrest” notice", "landing": True},
    {"id": "ai-instruction", "title": "Letter with hidden AI instructions",
     "kind": "Tests whether the checker can be talked out of a verdict", "landing": False,
     "alt": "Sample letter used to test hidden-instruction detection"},
    {"id": "sim-block-sms", "title": "SIM block text message",
     "kind": "Text saying your number will be blocked in 2 hours", "landing": False},
    {"id": "income-tax-intimation", "title": "Income tax intimation",
     "kind": "Income Tax Department notice, in the genuine format", "landing": False},
]

NAV_KEYS = {"try": "try", "how-it-works": "how", "evidence": "evidence", "judges": "judges"}

VERDICT_CLASS = {"likely_scam": "stamp-scam", "consistent_with_genuine": "stamp-ok", "cant_tell": "stamp-unsure"}
VERDICT_FALLBACK_LABEL = {"likely_scam": "Likely scam",
                          "consistent_with_genuine": "Consistent with a genuine letter. Confirm on the official number.",
                          "cant_tell": "Can't tell"}
SEVERITY_ORDER = {"strong": 0, "medium": 1, "info": 2}
SEVERITY_LABEL = {"strong": "Strong sign", "medium": "Warning sign", "info": "Note"}
MOCK_NOTE = "Illustrative result, not from the live checker. It will be replaced by live output before launch."
REDACTED_TEXT = "[instruction aimed at AI tools — hidden for safety, visible in the letter]"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]

ICONS = {
    "stamp-scam": '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 2h8l6 6v8l-6 6H8l-6-6V8z" '
                  'fill="none" stroke="currentColor" stroke-width="2"/><path d="M12 7v6" stroke="currentColor" '
                  'stroke-width="2.4" stroke-linecap="round"/><circle cx="12" cy="17" r="1.4" fill="currentColor"/></svg>',
    "stamp-ok": '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M6.6 10.8a15.1 '
                '15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25c1.1.37 2.3.57 3.6.57a1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 '
                '3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.57 3.57a1 1 0 0 1-.25 1z"/></svg>',
    "stamp-unsure": '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10" '
                    'fill="none" stroke="currentColor" stroke-width="2"/><path d="M9.2 9.3a2.9 2.9 0 1 1 4 2.7c-.8.4-1.2 '
                    '1-1.2 1.8v.6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/><circle '
                    'cx="12" cy="17.6" r="1.3" fill="currentColor"/></svg>',
}

FALLBACK_REPORT_CHANNELS = [
    ("India: National Cyber Crime Reporting Portal, helpline 1930", "https://cybercrime.gov.in"),
    ("United States: FTC", "https://reportfraud.ftc.gov"),
    ("United Kingdom: Report Fraud (formerly Action Fraud), 0300 123 2040", "https://www.reportfraud.police.uk"),
]

warnings: list[str] = []


def warn(message: str) -> None:
    warnings.append(message)
    print(f"warning: {message}", file=sys.stderr)


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


# ---------- sample data ----------

def result_path(sample_id: str) -> Path | None:
    """Live results win; offline results (mock: true) stand in until the live run has produced one."""
    for path in (SAMPLES / "results" / f"{sample_id}.json", SAMPLES / "results" / "mock" / f"{sample_id}.json"):
        if path.exists():
            return path
    return None


def load_result(sample_id: str) -> dict | None:
    path = result_path(sample_id)
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        warn(f"{path.name} is not valid JSON ({exc}); treating as missing")
        return None
    return sanitize_result(data)


def check_part(data: dict) -> dict:
    """Results may be the /api/check response itself, or wrap it as {"check": {...}}."""
    return data["check"] if isinstance(data.get("check"), dict) else data


def sanitize_result(data: dict) -> dict:
    """Public sample JSON must never carry letter text or an unredacted AI-instruction quote."""
    data = dict(data)
    data.pop("letter_text", None)
    check = check_part(data)
    check.pop("letter_text", None)
    for flag in check.get("flags") or []:
        if flag.get("rule") in ("ai_instruction", "injection_detected_model"):
            flag["quote"] = None
            flag["quote_redacted"] = True
    return data


PREVIEW_WIDTH = 720  # landing cards show letters at about 360 CSS px; tiles at 60


def letter_preview(sample_id: str, out: Path) -> str | None:
    """A small JPEG of the letter for <img> tags, so a phone doesn't download six full-size PNGs.
    Written during copy_samples when Pillow is available; otherwise the full PNG is used."""
    path = out / "samples" / "letters" / "preview" / f"{sample_id}.jpg"
    return f"/samples/letters/preview/{sample_id}.jpg" if path.exists() else letter_image(sample_id)


def write_previews(letters_out: Path) -> None:
    try:
        from PIL import Image
    except ImportError:
        warn("Pillow is not installed; sample images are served at full size")
        return
    preview_dir = letters_out / "preview"
    preview_dir.mkdir(exist_ok=True)
    for png in sorted(letters_out.glob("*.png")):
        image = Image.open(png).convert("RGB")
        if image.width > PREVIEW_WIDTH:
            image = image.resize((PREVIEW_WIDTH, round(image.height * PREVIEW_WIDTH / image.width)), Image.LANCZOS)
        image.save(preview_dir / f"{png.stem}.jpg", "JPEG", quality=82, optimize=True, progressive=True)


def letter_image(sample_id: str) -> str | None:
    path = SAMPLES / "letters" / f"{sample_id}.png"
    return f"/samples/letters/{sample_id}.png" if path.exists() else None


def pretty_date(iso: str | None) -> str | None:
    try:
        d = date.fromisoformat(iso or "")
    except ValueError:
        return None
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def host_of(url: str | None) -> str:
    return (urlparse(url or "").hostname or "").removeprefix("www.") if url else ""


# ---------- rendering ----------

def render_stamp(check: dict) -> str:
    verdict = check.get("verdict")
    cls = VERDICT_CLASS.get(verdict, "stamp-unsure")
    label = check.get("verdict_label") or VERDICT_FALLBACK_LABEL.get(verdict, "Can't tell")
    return f'<p class="stamp {cls}">{ICONS[cls]}<span>{esc(label)}</span></p>'


def render_flag(flag: dict) -> str:
    severity = flag.get("severity") if flag.get("severity") in SEVERITY_LABEL else "info"
    parts = [f'<li class="sev-block-{severity}">',
             f'<p class="flag-title"><span class="sev sev-{severity}">{SEVERITY_LABEL[severity]}</span>'
             f'<span>{esc(flag.get("title"))}</span></p>']
    if flag.get("quote_redacted"):
        parts.append(f'<blockquote class="quote redacted">{esc(REDACTED_TEXT)}</blockquote>')
    elif flag.get("quote"):
        parts.append('<blockquote class="quote"><span class="quote-label">From the letter</span>'
                     f'“{esc(flag["quote"])}”</blockquote>')
    if flag.get("why"):
        parts.append(f'<p class="why">{esc(flag["why"])}</p>')
    parts.append("</li>")
    return "".join(parts)


def render_official(check: dict) -> str:
    verdict = check.get("verdict")
    agency = check.get("agency") or None
    out = ['<div class="official">']
    if agency and (agency.get("official_phone") or agency.get("official_site")):
        title = {"likely_scam": "Do not call the number on this letter.",
                 "consistent_with_genuine": "Confirm it on the official number before you act."
                 }.get(verdict, "Check with the organisation directly, not with the number in the letter.")
        out.append(f'<p class="official-title">{esc(title)}</p>')
        if agency.get("official_phone"):
            phone = agency["official_phone"]
            tel = re.sub(r"[^\d+]", "", phone)
            out.append(f'<p>Official {esc(agency.get("name"))} line:<br>'
                       f'<a class="phone" href="tel:{esc(tel)}">{esc(phone)}</a></p>')
        else:
            site = agency["official_site"]
            out.append(f'<p>Official {esc(agency.get("name"))} website: '
                       f'<a href="{esc(site)}" rel="noopener">{esc(host_of(site))}</a></p>')
        if agency.get("source_url"):
            checked = pretty_date(agency.get("checked_on"))
            checked_txt = f", checked {esc(checked)}" if checked else ""
            out.append(f'<p class="source">Source: <a href="{esc(agency["source_url"])}" rel="noopener">'
                       f'{esc(host_of(agency["source_url"]))}</a>{checked_txt}</p>')
    else:
        out.append('<p class="official-title">We could not match the sender to an official contact.</p>'
                   "<p>Find the organisation's number yourself, on its official website or on a bill you already "
                   "trust. Do not use the number in this letter.</p>")
    if verdict == "likely_scam":
        channel = (agency or {}).get("report_channel") or check.get("report_channel")
        if channel and channel.get("url"):
            out.append(f'<p class="report">Report it: <a href="{esc(channel["url"])}" rel="noopener">'
                       f'{esc(channel.get("name") or host_of(channel["url"]))}</a></p>')
        else:
            links = "".join(f'<li><a href="{url}" rel="noopener">{esc(name)}</a></li>'
                            for name, url in FALLBACK_REPORT_CHANNELS)
            out.append(f'<div class="report"><p>Report it:</p><ul class="plain-list">{links}</ul></div>')
    out.append("</div>")
    return "".join(out)


def render_landing_card(entry: dict, out: Path) -> str:
    sid, title = entry["id"], entry["title"]
    data = load_result(sid)
    image = letter_image(sid)
    if image is None:
        warn(f"no letter image samples/letters/{sid}.png; landing card renders without it")
    head = [f'<article class="sample-card" id="sample-{esc(sid)}" aria-labelledby="sample-{esc(sid)}-title">']
    if image:
        head.append(f'<a class="letter-peek" href="{esc(image)}"><img src="{esc(letter_preview(sid, out))}" '
                    f'alt="{esc(entry.get("alt") or "The sample letter: " + title)}" loading="lazy"></a>')
    head.append('<div class="body">')
    head.append(f'<h3 id="sample-{esc(sid)}-title">{esc(title)}</h3><p class="kind">{esc(entry["kind"])}</p>')

    if data is None:
        warn(f"no result samples/results/{sid}.json; rendering a 'result coming soon' card")
        return "".join(head) + ('<p class="stamp stamp-pending"><span>Result coming soon</span></p>'
                                "<p class=\"headline muted\">This sample's result is being prepared. "
                                'Meanwhile you can <a href="/try/">check a letter of your own</a>.</p></div></article>')

    check = check_part(data)
    body = [render_stamp(check)]
    if check.get("headline"):
        body.append(f'<p class="headline">{esc(check["headline"])}</p>')
    if data.get("mock"):
        warn(f"{result_path(sid).relative_to(ROOT).as_posix()} is mock data")
        body.append(f'<p class="mock-note">{esc(MOCK_NOTE)}</p>')

    flags = sorted(check.get("flags") or [], key=lambda f: SEVERITY_ORDER.get(f.get("severity"), 3))
    shown = [f for f in flags if f.get("severity") != "info"][:2] or flags[:2]
    if shown:
        body.append('<ul class="flags">' + "".join(render_flag(f) for f in shown) + "</ul>")
        if len(flags) > len(shown):
            body.append(f'<p class="muted small">{len(flags) - len(shown)} more in the full result.</p>')
    else:
        checks = sum(1 for t in check.get("trace") or [] if str(t.get("step", "")).startswith("rule:"))
        body.append(f'<p class="muted">No warning signs found{f" in {checks} rule checks" if checks else ""}.</p>')

    deadlines = (check.get("extracted") or {}).get("deadlines") or []
    if deadlines and check.get("verdict") != "likely_scam":
        first = deadlines[0]
        when = pretty_date(first.get("date"))
        if when:
            basis = (f", worked out in code as {esc(first['computed_from'].replace('_', ' '))}"
                     if first.get("computed_from") else "")
            body.append(f'<p class="deadline-line">Deadline: <strong>{esc(when)}</strong>{basis}.</p>')
            if first.get("what"):
                body.append(f'<p class="deadline-line muted">{esc(first["what"].rstrip("."))}.</p>')

    body.append(render_official(check))
    body.append(f'<p class="more"><a href="/try/?sample={esc(sid)}">Open the full result and every check</a></p>')
    return "".join(head) + "".join(body) + "</div></article>"


def render_tiles(out: Path) -> str:
    items = []
    for entry in CATALOG:
        sid = entry["id"]
        ready = result_path(sid) is not None
        image = letter_image(sid)
        preview = letter_preview(sid, out) if image else None
        thumb = (f'<img src="{esc(preview)}" alt="" loading="lazy">' if image
                 else '<span aria-hidden="true">¶</span>')
        sub = esc(entry["kind"]) if ready else "Result coming soon"
        disabled = "" if ready else " disabled"
        items.append(f'<li><button type="button" class="tile" data-sample="{esc(sid)}" '
                     f'data-title="{esc(entry["title"])}" data-alt="{esc(entry.get("alt") or "")}" '
                     f'data-image="{esc(image or "")}" data-preview="{esc(preview or "")}"{disabled}>'
                     f'<span class="tile-thumb">{thumb}</span>'
                     f'<span><span class="tile-title">{esc(entry["title"])}</span>'
                     f'<span class="tile-sub">{sub}</span></span></button></li>')
    return "\n".join(items)


# ---------- page assembly ----------

def nav_key_for(page: Path, out: Path) -> str | None:
    rel = page.relative_to(out).parts
    return NAV_KEYS.get(rel[0]) if len(rel) > 1 else None


def render_header(key: str | None) -> str:
    header = (PARTIALS / "header.html").read_text(encoding="utf-8")
    if key:
        header = header.replace(f'data-nav="{key}"', f'data-nav="{key}" aria-current="page"')
    if key == "try":  # the page itself is the call to action
        header = re.sub(r'\s*<a class="btn btn-small header-cta"[^>]*>.*?</a>', "", header)
    return header


def absolutize_meta(text: str, site_url: str) -> str:
    if not site_url:
        return text
    base = site_url.rstrip("/")
    return re.sub(r'(<meta property="og:(?:url|image)" content=")(/[^"]*)"', lambda m: f'{m.group(1)}{base}{m.group(2)}"',
                  text)


def build_page(page: Path, out: Path, site_url: str, landing_cards: str, tiles: str) -> None:
    text = page.read_text(encoding="utf-8")
    text = text.replace("<!-- @head -->", (PARTIALS / "head.html").read_text(encoding="utf-8"))
    text = text.replace("<!-- @header -->", render_header(nav_key_for(page, out)))
    text = text.replace("<!-- @footer -->", (PARTIALS / "footer.html").read_text(encoding="utf-8"))
    text = text.replace("<!-- @samples:landing -->", landing_cards)
    text = text.replace("<!-- @samples:tiles -->", tiles)
    text = absolutize_meta(text, site_url)
    leftover = re.findall(r"<!-- @[\w:-]+ -->", text)
    if leftover:
        warn(f"{page.relative_to(out)} has unknown markers: {', '.join(sorted(set(leftover)))}")
    page.write_text(text, encoding="utf-8")


def copy_samples(out: Path) -> None:
    results_out = out / "samples" / "results"
    letters_out = out / "samples" / "letters"
    results_out.mkdir(parents=True, exist_ok=True)
    letters_out.mkdir(parents=True, exist_ok=True)
    for entry in CATALOG:
        data = load_result(entry["id"])
        if data is not None:
            (results_out / f"{entry['id']}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1),
                                                             encoding="utf-8")
    for path in sorted((SAMPLES / "letters").glob("*.png")):
        shutil.copy2(path, letters_out / path.name)
    write_previews(letters_out)


def safe_out_dir(raw: str) -> Path:
    out = (ROOT / raw).resolve() if not os.path.isabs(raw) else Path(raw).resolve()
    if out == ROOT or ROOT not in out.parents or out in (SITE, SAMPLES) or SITE in out.parents:
        raise SystemExit(f"refusing to build into {out}: pick a directory inside the project, e.g. dist")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="dist")
    parser.add_argument("--site-url", default=os.environ.get("SITE_URL", ""))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    out = safe_out_dir(args.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(SITE, out, ignore=shutil.ignore_patterns("_partials", ".DS_Store", "Thumbs.db"))
    copy_samples(out)

    landing = [e for e in CATALOG if e["landing"]]
    landing_cards = "\n".join(render_landing_card(e, out) for e in landing)
    tiles = render_tiles(out)
    for page in sorted(out.rglob("*.html")):
        if "vendor" in page.relative_to(out).parts:
            continue
        build_page(page, out, args.site_url, landing_cards, tiles)

    if args.strict:
        blocking = [e["id"] for e in CATALOG
                    if ((data := load_result(e["id"])) is None and e["landing"]) or (data and data.get("mock"))]
        if blocking:
            print(f"error: --strict and these samples are missing (landing) or mock: {', '.join(blocking)}",
                  file=sys.stderr)
            return 1

    print(f"built {out.relative_to(ROOT)} with {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
