"""Render the share image and the cover image from their HTML sources with headless Edge or Chrome.

    python scripts/render_art.py

docs/art/og.html    -> site/assets/og.png  (1200x630, Open Graph / link previews)
docs/art/cover.html -> docs/cover.png      (1200x675, submission cover, no text)

Screenshots are taken at 2x and scaled down with Pillow, which gives smoother text and edges than 1x.
"""
import sys
import tempfile
from pathlib import Path

from PIL import Image

from render_letters import find_browser, screenshot

ROOT = Path(__file__).resolve().parents[1]
ART = [
    (ROOT / "docs" / "art" / "og.html", ROOT / "site" / "assets" / "og.png", (1200, 630)),
    (ROOT / "docs" / "art" / "cover.html", ROOT / "docs" / "cover.png", (1200, 675)),
]


def main():
    browser = find_browser()
    for source, target, size in ART:
        with tempfile.TemporaryDirectory(prefix="plainly-art-") as tmp:
            raw = Path(tmp) / "shot.png"
            screenshot(browser, source, raw, 2)
            image = Image.open(raw).convert("RGB")
            # The window can include a few pixels of browser chrome; keep exactly the canvas, then scale.
            image = image.crop((0, 0, size[0] * 2, size[1] * 2)).resize(size, Image.LANCZOS)
            image.save(target, optimize=True)
        print(f"  {target.relative_to(ROOT).as_posix():24} {size[0]}x{size[1]}  {target.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
