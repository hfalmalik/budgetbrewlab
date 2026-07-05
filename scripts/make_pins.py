"""
make_pins.py — Pinterest pin generator for BudgetBrewLab.

For every article in content/*.md, renders a 1000x1500 branded pin PNG into
pins/ and writes pins/captions.txt with a ready-to-paste title, description
and destination link per pin. Pinning itself stays manual (or via a scheduler
like Tailwind later) — this makes it a 30-second copy-paste per pin.

Usage:  python scripts/make_pins.py          # all articles (skips existing)
        python scripts/make_pins.py --force  # regenerate all
"""

import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
PINS = ROOT / "pins"
FONT_DIR = Path(r"C:\Windows\Fonts")

W, H = 1000, 1500  # Pinterest's recommended 2:3
BG_TOP = (24, 18, 14)      # coffee-dark
BG_BOTTOM = (48, 34, 24)
ACCENT = (212, 148, 74)    # roasted amber
ACCENT2 = (240, 200, 140)
WHITE = (248, 245, 240)
MUTED = (196, 184, 170)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def fit(draw, text, path, max_w, max_h, start, floor):
    size = start
    while size >= floor:
        f = ImageFont.truetype(path, size)
        ls = wrap(draw, text, f, max_w)
        lh = int(sum(f.getmetrics()) * 1.06)
        if lh * len(ls) <= max_h and len(ls) <= 6:
            return f, ls, lh
        size -= 4
    f = ImageFont.truetype(path, floor)
    ls = wrap(draw, text, f, max_w)
    return f, ls, int(sum(f.getmetrics()) * 1.06)


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    meta = {}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    meta[k.strip().lower()] = v.strip().strip('"')
    return meta


def render_pin(title, category, out_path):
    img = Image.new("RGB", (W, H))
    d0 = ImageDraw.Draw(img)
    for y in range(H):
        d0.line([(0, y), (W, y)], fill=lerp(BG_TOP, BG_BOTTOM, y / (H - 1)))
    img = img.convert("RGBA")

    # soft amber glow top-right
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dg = ImageDraw.Draw(glow)
    dg.ellipse([W - 500, -220, W + 220, 500], fill=ACCENT + (46,))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    img.alpha_composite(glow)
    img = img.convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")

    # frame + top/bottom bands
    d.rectangle([0, 0, W, 16], fill=ACCENT + (255,))
    d.rectangle([0, H - 16, W, H], fill=ACCENT + (255,))
    d.rectangle([36, 36, W - 36, H - 36], outline=ACCENT + (90,), width=2)

    bold = str(FONT_DIR / "segoeuib.ttf")
    semi = str(FONT_DIR / "seguisb.ttf")
    margin = 90
    max_w = W - 2 * margin

    kicker_font = ImageFont.truetype(semi, 40)
    kicker = category.upper() + "  ·  BUDGET COFFEE GEAR"
    kw = d.textlength(kicker, font=kicker_font)
    d.text(((W - kw) / 2, 150), kicker, font=kicker_font, fill=ACCENT2)

    tfont, tlines, tlh = fit(d, title, bold, max_w, 700, 96, 54)
    y = (H - tlh * len(tlines)) / 2 - 60
    for ln in tlines:
        lw = d.textlength(ln, font=tfont)
        d.text(((W - lw) / 2 + 4, y + 4), ln, font=tfont, fill=(0, 0, 0, 150))
        d.text(((W - lw) / 2, y), ln, font=tfont, fill=WHITE)
        y += tlh

    y += 50
    d.rectangle([(W - 220) / 2, y, (W + 220) / 2, y + 7], fill=ACCENT + (255,))

    brand_font = ImageFont.truetype(semi, 44)
    brand = "BudgetBrewLab"
    bw = d.textlength(brand, font=brand_font)
    d.text(((W - bw) / 2, H - 190), brand, font=brand_font, fill=WHITE)
    site_font = ImageFont.truetype(semi, 30)
    site = "hfalmalik.github.io/budgetbrewlab"
    sw = d.textlength(site, font=site_font)
    d.text(((W - sw) / 2, H - 130), site, font=site_font, fill=MUTED)

    img.save(out_path, "PNG")


def main(argv):
    force = "--force" in argv
    PINS.mkdir(exist_ok=True)
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    site_url = cfg["site_url"].rstrip("/")

    captions = []
    made = 0
    for md in sorted(CONTENT.glob("*.md")):
        meta = frontmatter(md)
        if not meta.get("title"):
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", md.stem.lower()).strip("-")
        out = PINS / f"{slug}.png"
        # pin title: strip the year/parenthetical noise for the image
        img_title = re.sub(r"\s*\(.*?\)\s*", " ", meta["title"])
        img_title = re.sub(r"\s+in \d{4}", "", img_title).strip()
        if force or not out.exists():
            render_pin(img_title, meta.get("category", "Coffee"), out)
            made += 1
            print(f"pin  {out.name}")
        captions.append(
            f"PIN: {out.name}\n"
            f"Title (max 100 chars): {meta['title'][:100]}\n"
            f"Description: {meta['description']} #budgetcoffee #coffeegear "
            f"#homebarista #coffeelover\n"
            f"Link: {site_url}/{slug}.html\n"
        )
    (PINS / "captions.txt").write_text("\n".join(captions), encoding="utf-8")
    print(f"{made} pin(s) rendered, captions.txt updated -> {PINS}")


if __name__ == "__main__":
    main(sys.argv[1:])
