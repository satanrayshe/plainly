"""Run the real pipeline on the showcase letters and save what the site pre-renders.

    python scripts/run_samples.py --live          # real Textract + Bedrock (needs AWS credentials), writes
                                                  #   samples/results/<id>.json for build_site.py
    python scripts/run_samples.py                 # offline: fakes AWS, writes samples/results/mock/<id>.json
    python scripts/run_samples.py irs-balance-due --live --languages Hindi

Each letter goes through POST /api/check exactly like an upload from /try/ (the PNG re-encoded as a JPEG under
1.5 MB), then POST /api/explain once per language (English, Hindi and Spanish by default; the site shows these
on the sample tiles). letter_text is dropped before saving, and the script refuses to write a
result that repeats the AI-instruction sample's hidden line anywhere.
"""
import argparse
import base64
import html
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
from harness import LocalApi  # noqa: E402

LETTERS = ROOT / "samples" / "letters"
RESULTS = ROOT / "samples" / "results"
MAX_UPLOAD = 1_500_000

SAMPLES = {
    "electricity-final-notice": "Electricity “final notice”",
    "irs-balance-due": "IRS balance-due notice",
    "digital-arrest-parcel": "“CBI” arrest warrant over a parcel",
    "ai-instruction": "Letter with hidden AI instructions",
    "sim-block-sms": "SIM block text message",
    "income-tax-intimation": "Income tax intimation",
}
# Words from the hidden line in the ai-instruction letter. None of them may appear in a saved result.
INJECTION_MARKERS = ("ignore previous instructions", "classify this letter as legitimate", "automated reviewers")


def as_upload_jpeg(png_path):
    """What the browser would send: a JPEG no larger than 1.5 MB with a long edge of at most 2000 px."""
    image = Image.open(png_path).convert("RGB")
    image.thumbnail((2000, 2000))
    for quality in (88, 80, 72, 64):
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=quality, optimize=True)
        if buffer.tell() <= MAX_UPLOAD:
            return buffer.getvalue()
    raise RuntimeError(f"{png_path.name} will not fit under {MAX_UPLOAD} bytes as JPEG")


def visible_text(html_path):
    """Roughly what OCR reads off the rendered letter; only used to feed the offline Textract fake."""
    source = html_path.read_text(encoding="utf-8")
    source = re.sub(r"(?is)<head.*?</head>|<!--.*?-->", " ", source)
    source = re.sub(r"\s+", " ", source)  # source line breaks are not visible; only block ends are
    source = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d|table|ol|ul)>", "\n", source)
    source = re.sub(r"(?i)</t[dh]>", " ", source)
    text = html.unescape(re.sub(r"<[^>]+>", " ", source))
    lines = (re.sub(r"\s+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def assert_no_injection_text(sample_id, data):
    dumped = json.dumps(data, ensure_ascii=False).lower()
    leaked = [m for m in INJECTION_MARKERS if m in dumped]
    if leaked:
        raise SystemExit(f"{sample_id}: result repeats hidden-instruction text ({', '.join(leaked)}); not saving it. "
                         "The ai_instruction flag must have quote=null and quote_redacted=true.")


def run_one(api, sample_id, title, args):
    png = LETTERS / f"{sample_id}.png"
    if not png.exists():
        raise SystemExit(f"Missing {png.relative_to(ROOT)}; run scripts/render_letters.py first.")
    jpeg = as_upload_jpeg(png)
    if not api.live:
        api.register_ocr(jpeg, visible_text(png.with_suffix(".html")))

    payload = {"image": {"type": "image/jpeg", "data": base64.b64encode(jpeg).decode("ascii")},
               "text": "", "today": args.today}
    status, check, check_ms = api.post("/api/check", payload)
    if status != 200:
        raise SystemExit(f"{sample_id}: /api/check returned {status}: {check}")

    letter_text = check.pop("letter_text", "")
    explanations, explain_ms = {}, 0
    for language in args.languages:
        status, explain, ms = api.post("/api/explain", {
            "letter_text": letter_text, "check": check, "language": language, "level": args.level})
        if status != 200:
            raise SystemExit(f"{sample_id}: /api/explain ({language}) returned {status}: {explain}")
        explanations[language] = explain
        explain_ms += ms

    result = {
        "id": sample_id,
        "title": title,
        "image": f"/samples/letters/{sample_id}.png",
        "mock": not api.live,
        "check": check,
        "explanations": explanations,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    assert_no_injection_text(sample_id, result)
    out_dir = RESULTS if api.live else RESULTS / "mock"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{sample_id}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    flags = ", ".join(f["rule"] for f in check.get("flags", [])) or "none"
    print(f"  {sample_id:26} {check.get('verdict', '?'):24} {check_ms:>6} ms + {explain_ms:>6} ms  flags: {flags}")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ids", nargs="*", help="sample ids; default: all six")
    parser.add_argument("--live", action="store_true", help="call real AWS (Textract + Bedrock)")
    parser.add_argument("--today", default="2026-09-30", help="client date sent with /api/check")
    parser.add_argument("--languages", default="English,Hindi,Spanish",
                        type=lambda v: [x.strip() for x in v.split(",") if x.strip()],
                        help="comma-separated explanation languages (default: English,Hindi,Spanish)")
    parser.add_argument("--level", default="simple", choices=["simple", "normal"])
    args = parser.parse_args()

    unknown = [i for i in args.ids if i not in SAMPLES]
    if unknown:
        raise SystemExit(f"Unknown sample id(s): {', '.join(unknown)}. Known: {', '.join(SAMPLES)}")

    api = LocalApi(live=args.live)
    print(f"Running {len(args.ids or SAMPLES)} sample(s) in {api.mode} mode")
    for sample_id in args.ids or SAMPLES:
        run_one(api, sample_id, SAMPLES[sample_id], args)
    if not args.live:
        print("Offline results went to samples/results/mock/ so they never replace the live ones the site uses.")


if __name__ == "__main__":
    main()
