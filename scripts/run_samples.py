"""Run the pipeline on the showcase letters and save what the site pre-renders.

    python scripts/run_samples.py                 # production path (AI_MODE=off): rules reader + templates,
                                                  #   no AWS needed; writes samples/results/<id>.json
    python scripts/run_samples.py --refresh-text  # first rebuild samples/letters/<id>.txt from the HTML
    python scripts/run_samples.py --ai-mock       # AI_MODE=on with faked Textract/Bedrock -> samples/results/mock/
    python scripts/run_samples.py --live          # AI_MODE=on with real Textract + Bedrock (needs an account that
                                                  #   has them; the Free plan does not) -> samples/results/<id>.json
    python scripts/run_samples.py irs-balance-due --languages Hindi

Production (default): on the live site the browser reads a photo on the device (Tesseract.js) and sends only the
text. Here each sample's text comes from samples/letters/<id>.txt, the letter's visible text taken from its HTML
source (the watermark left out; in ai-instruction the faint line aimed at AI tools is kept, because it is part of the
letter). That stands in for what on-device OCR would read; it is not an OCR run. Each letter goes through
POST /api/check with text_source "device_ocr", then POST /api/explain in English, Hindi and Spanish.

AI_MODE=on (--ai-mock, --live): the PNG is re-encoded as a JPEG under 1.5 MB and uploaded like the old /try/ page did.

letter_text is dropped before saving, and the script refuses to write a result that repeats the AI-instruction
sample's hidden line anywhere.
"""
import argparse
import base64
import html
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "eval"))
from harness import LocalApi  # noqa: E402

LETTERS = ROOT / "samples" / "letters"
RESULTS = ROOT / "samples" / "results"
MAX_UPLOAD = 1_500_000
TEXT_SOURCE_LABEL = "device_ocr-equivalent (sample text)"

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
    """What the AI_MODE=on browser sent: a JPEG no larger than 1.5 MB with a long edge of at most 2000 px."""
    from PIL import Image  # only the AI_MODE=on runs need Pillow

    image = Image.open(png_path).convert("RGB")
    image.thumbnail((2000, 2000))
    for quality in (88, 80, 72, 64):
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=quality, optimize=True)
        if buffer.tell() <= MAX_UPLOAD:
            return buffer.getvalue()
    raise RuntimeError(f"{png_path.name} will not fit under {MAX_UPLOAD} bytes as JPEG")


def visible_text(html_path, keep_watermark=True):
    """Roughly what OCR reads off the rendered letter: block elements become lines, markup and <head> go.

    keep_watermark=False drops the diagonal "SAMPLE - NOT A REAL NOTICE" stamp (the samples/letters/<id>.txt files);
    the AI_MODE=on fake Textract still gets it, as before.
    """
    source = html_path.read_text(encoding="utf-8")
    source = re.sub(r"(?is)<head.*?</head>|<!--.*?-->", " ", source)
    if not keep_watermark:
        source = re.sub(r'(?is)<div class="watermark">.*?</div>', " ", source)
    source = re.sub(r"\s+", " ", source)  # source line breaks are not visible; only block ends are
    source = re.sub(r"(?i)<br\s*/?>|</(p|div|li|tr|h\d|table|ol|ul)>", "\n", source)
    source = re.sub(r"(?i)</t[dh]>", " ", source)
    text = html.unescape(re.sub(r"<[^>]+>", " ", source))
    lines = (re.sub(r"\s+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def sample_text(sample_id, refresh=False):
    """samples/letters/<id>.txt, written from the HTML when missing (or when refresh is asked for)."""
    path = LETTERS / f"{sample_id}.txt"
    if refresh or not path.exists():
        source = LETTERS / f"{sample_id}.html"
        if not source.exists():
            raise SystemExit(f"Missing {source.relative_to(ROOT)}")
        path.write_text(visible_text(source, keep_watermark=False) + "\n", encoding="utf-8", newline="\n")
        print(f"  wrote {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8").strip()


def assert_no_injection_text(sample_id, data):
    dumped = json.dumps(data, ensure_ascii=False).lower()
    leaked = [m for m in INJECTION_MARKERS if m in dumped]
    if leaked:
        raise SystemExit(f"{sample_id}: result repeats hidden-instruction text ({', '.join(leaked)}); not saving it. "
                         "The ai_instruction flag must have quote=null and quote_redacted=true.")


def check_payload(api, sample_id, args):
    if args.mode == "off":
        return {"text": sample_text(sample_id, args.refresh_text), "text_source": "device_ocr", "today": args.today}
    png = LETTERS / f"{sample_id}.png"
    if not png.exists():
        raise SystemExit(f"Missing {png.relative_to(ROOT)}; run scripts/render_letters.py first.")
    jpeg = as_upload_jpeg(png)
    if not api.live:
        api.register_ocr(jpeg, visible_text(png.with_suffix(".html")))
    return {"image": {"type": "image/jpeg", "data": base64.b64encode(jpeg).decode("ascii")}, "text": "",
            "today": args.today}


def run_one(api, sample_id, title, args):
    status, check, check_ms = api.post("/api/check", check_payload(api, sample_id, args))
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

    mock = args.mode == "ai-mock"
    result = {
        "id": sample_id,
        "title": title,
        "image": f"/samples/letters/{sample_id}.png",
        "mock": mock,
        "ai_mode": "off" if args.mode == "off" else "on",
        "reader": "rules" if args.mode == "off" else ("mock-model" if mock else "bedrock"),
        "text_source": TEXT_SOURCE_LABEL if args.mode == "off" else "image upload",
        "check": check,
        "explanations": explanations,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    assert_no_injection_text(sample_id, result)
    out_dir = RESULTS / "mock" if mock else RESULTS
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{sample_id}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    flags = ", ".join(f["rule"] for f in check.get("flags", [])) or "none"
    print(f"  {sample_id:26} {check.get('verdict', '?'):24} {check_ms:>6} ms + {explain_ms:>6} ms  flags: {flags}")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ids", nargs="*", help="sample ids; default: all six")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--ai-mock", dest="mode", action="store_const", const="ai-mock",
                      help="AI_MODE=on with faked Textract/Bedrock (writes samples/results/mock/)")
    mode.add_argument("--live", dest="mode", action="store_const", const="live",
                      help="AI_MODE=on with real Textract + Bedrock (needs AWS credentials and model access)")
    parser.set_defaults(mode="off")
    parser.add_argument("--refresh-text", action="store_true",
                        help="rebuild samples/letters/<id>.txt from the HTML before running (production mode)")
    parser.add_argument("--today", default="2026-09-30", help="client date sent with /api/check")
    parser.add_argument("--languages", default="English,Hindi,Spanish",
                        type=lambda v: [x.strip() for x in v.split(",") if x.strip()],
                        help="comma-separated explanation languages (default: English,Hindi,Spanish)")
    parser.add_argument("--level", default="simple", choices=["simple", "normal"])
    args = parser.parse_args()

    unknown = [i for i in args.ids if i not in SAMPLES]
    if unknown:
        raise SystemExit(f"Unknown sample id(s): {', '.join(unknown)}. Known: {', '.join(SAMPLES)}")

    os.environ["AI_MODE"] = "off" if args.mode == "off" else "on"
    api = LocalApi(live=args.mode == "live")
    label = {"off": "production (AI_MODE=off: rules reader + templates, no AWS)",
             "ai-mock": "AI_MODE=on with faked AWS", "live": "AI_MODE=on with live AWS"}[args.mode]
    print(f"Running {len(args.ids or SAMPLES)} sample(s): {label}")
    for sample_id in args.ids or SAMPLES:
        run_one(api, sample_id, SAMPLES[sample_id], args)
    if args.mode == "ai-mock":
        print("Mock results went to samples/results/mock/ so they never replace the ones the site uses.")


if __name__ == "__main__":
    main()
