"""Render the sample letters (samples/letters/*.html) to PNG with headless Edge or Chrome.

    python scripts/render_letters.py                 # every letter
    python scripts/render_letters.py irs-balance-due # just one
    python scripts/render_letters.py --scale 2 --browser "C:/path/to/chrome.exe"

Each HTML file declares its canvas in <meta name="plainly:render" content="width=794,height=1123">
(A4 at 96 dpi for letters, a phone viewport for SMS screenshots). The screenshot is taken at a device scale
factor for crisp text, then shrunk with Pillow until the file is under the upload limit the site uses.
Needs Pillow (pip install pillow); the Lambda never imports this file.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LETTERS = ROOT / "samples" / "letters"
MAX_BYTES = 1_500_000
MAX_LONG_EDGE = 2000  # same cap the browser applies to uploads

BROWSER_CANDIDATES = [
    r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe",
    r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe",
    r"%ProgramFiles%\Google\Chrome\Application\chrome.exe",
    r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe",
    r"%LocalAppData%\Google\Chrome\Application\chrome.exe",
]
RENDER_META = re.compile(r'<meta\s+name="plainly:render"\s+content="width=(\d+),\s*height=(\d+)"', re.I)


def find_browser(explicit=None):
    candidates = [explicit, os.environ.get("PLAINLY_BROWSER")] + [os.path.expandvars(p) for p in BROWSER_CANDIDATES]
    for path in candidates:
        if path and Path(path).is_file():
            return path
    for name in ("msedge", "chrome", "google-chrome", "chromium"):
        found = shutil.which(name)
        if found:
            return found
    sys.exit("No Edge or Chrome found. Pass --browser or set PLAINLY_BROWSER.")


def canvas_size(html_path):
    match = RENDER_META.search(html_path.read_text(encoding="utf-8"))
    return (int(match[1]), int(match[2])) if match else (794, 1123)


def screenshot(browser, html_path, out_path, scale):
    width, height = canvas_size(html_path)
    # A throwaway profile keeps headless runs from attaching to an Edge window the user already has open.
    with tempfile.TemporaryDirectory(prefix="plainly-render-") as profile:
        cmd = [
            browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
            "--no-default-browser-check", "--disable-extensions", f"--user-data-dir={profile}",
            f"--force-device-scale-factor={scale}", f"--window-size={width},{height}",
            "--default-background-color=ffffffff", f"--screenshot={out_path}", html_path.as_uri(),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    if not out_path.exists():
        raise RuntimeError(f"{html_path.name}: browser wrote no screenshot\n{result.stderr[-800:]}")


def shrink(png_path):
    """Cap the long edge, then trade colours and pixels for bytes until the PNG fits under MAX_BYTES."""
    image = Image.open(png_path).convert("RGB")
    if max(image.size) > MAX_LONG_EDGE:
        ratio = MAX_LONG_EDGE / max(image.size)
        image = image.resize((round(image.width * ratio), round(image.height * ratio)), Image.LANCZOS)
    image.save(png_path, optimize=True)
    step = 0
    while png_path.stat().st_size > MAX_BYTES:
        step += 1
        if step == 1:
            # Letters are mostly flat colour; a 256-colour palette usually cuts the size by 3-4x.
            image.quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(png_path, optimize=True)
            continue
        if step > 6:
            raise RuntimeError(f"{png_path.name} is still {png_path.stat().st_size} bytes")
        image = image.resize((round(image.width * 0.85), round(image.height * 0.85)), Image.LANCZOS)
        image.quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(png_path, optimize=True)
    return Image.open(png_path).size, png_path.stat().st_size


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ids", nargs="*", help="letter ids (file names without .html); default: all")
    parser.add_argument("--browser", help="path to msedge.exe or chrome.exe")
    parser.add_argument("--scale", type=float, default=2.0, help="device scale factor (default 2)")
    args = parser.parse_args()

    browser = find_browser(args.browser)
    pages = [LETTERS / f"{i}.html" for i in args.ids] if args.ids else sorted(LETTERS.glob("*.html"))
    missing = [p.name for p in pages if not p.exists()]
    if missing:
        sys.exit(f"Not found in {LETTERS}: {', '.join(missing)}")

    print(f"Rendering {len(pages)} letter(s) with {Path(browser).name} at scale {args.scale}")
    for page in pages:
        out = page.with_suffix(".png")
        out.unlink(missing_ok=True)
        screenshot(browser, page, out, args.scale)
        (w, h), size = shrink(out)
        print(f"  {out.relative_to(ROOT)}  {w}x{h}  {size / 1_000_000:.2f} MB")


if __name__ == "__main__":
    main()
