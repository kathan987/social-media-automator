"""Cinematic thumbnails for every Short (fonts: Anton + Bebas Neue from Google Fonts in assets/fonts).
  python thumbnail.py <video-slug>
Reads videos/<slug>/thumb.json and writes videos/<slug>/thumbnail.jpg (1080x1920, Shorts) and thumbnail-16x9.jpg
(1280x720, feed/search). Built from the video's own real assets (official art, cut-outs, frames), never AI likenesses.
thumb.json: {"bg": "path", "bg2": "path (optional: split screen, bg left/top, bg2 right/bottom)",
             "cutouts": [{"src": "path.png", "x": 0.5, "y": 1.0, "h": 0.62}],   # centre-x, bottom-y, height (fractions)
             "words": ["TOP LINE", "BIG LINE"], "accent": "#ff4fa3", "badge": "optional small corner text"}
Paths are relative to the repo root. Words: 2-3, never the title (yt-package rule).
  python tools/thumbnail.py <project-slug>"""
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE
FONTS = ROOT / "assets" / "fonts"


def cover(im, w, h):
    return ImageOps.fit(im.convert("RGB"), (w, h), Image.LANCZOS, centering=(0.5, 0.45))


def grade(im):
    """Teal shadows, warm highlights, more contrast: the 'cinematic' look."""
    im = ImageOps.autocontrast(im, cutoff=1)
    r, g, b = im.split()
    lum = ImageOps.grayscale(im)
    shadows = ImageOps.invert(lum).point(lambda v: int(v * 0.16))
    highs = lum.point(lambda v: int(max(0, v - 128) * 0.28))
    r = ImageChops.add(ImageChops.subtract(r, shadows), highs)
    b = ImageChops.subtract(ImageChops.add(b, shadows), highs)
    return Image.merge("RGB", (r, g, b))


def vignette(im, strength=0.75):
    w, h = im.size
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).ellipse([-w * 0.25, -h * 0.15, w * 1.25, h * 1.15], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(min(w, h) // 5))
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    return Image.composite(im, Image.blend(im, dark, strength), m)


def grain(im, amount=10):
    random.seed(7)  # same thumbnail every run
    noise = Image.effect_noise(im.size, amount).convert("RGB")
    return Image.blend(im, ImageChops.overlay(im, noise), 0.12)


def paste_cutout(canvas, src, x, y, h, accent):
    cut = Image.open(BASE / src).convert("RGBA")
    H = int(canvas.height * h)
    cut = cut.resize((max(1, int(cut.width * H / cut.height)), H), Image.LANCZOS)
    left, top = int(canvas.width * x - cut.width / 2), int(canvas.height * y - cut.height)
    glow = Image.new("RGBA", cut.size, accent)
    glow.putalpha(cut.split()[3].filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(18)))
    canvas.alpha_composite(glow, (left, top))
    canvas.alpha_composite(cut, (left, top))


def text(canvas, words, accent, big):
    d = ImageDraw.Draw(canvas)
    w = canvas.width
    top_f = ImageFont.truetype(str(FONTS / "Anton-Regular.ttf"), int(big * 0.42))
    big_f = ImageFont.truetype(str(FONTS / "Anton-Regular.ttf"), big)
    y = int(canvas.height * 0.05)
    for k, line in enumerate(words):
        f = top_f if (k == 0 and len(words) > 1) else big_f
        while d.textlength(line, font=f) > w * 0.92:
            f = ImageFont.truetype(f.path, int(f.size * 0.92))
        tw = d.textlength(line, font=f)
        fill = (255, 255, 255) if f is top_f else accent
        sw = max(4, f.size // 14)
        d.text(((w - tw) / 2 + 6, y + 8), line, font=f, fill=(0, 0, 0), stroke_width=sw, stroke_fill=(0, 0, 0))
        d.text(((w - tw) / 2, y), line, font=f, fill=fill, stroke_width=sw, stroke_fill=(0, 0, 0))
        y += int(f.size * 1.02)


def build(spec, w, h):
    if spec.get("bg2"):
        a, b = Image.open(BASE / spec["bg"]), Image.open(BASE / spec["bg2"])
        bg = Image.new("RGB", (w, h))
        if w > h:
            bg.paste(cover(a, w // 2, h), (0, 0)); bg.paste(cover(b, w - w // 2, h), (w // 2, 0))
        else:
            bg.paste(cover(a, w, h // 2), (0, 0)); bg.paste(cover(b, w, h - h // 2), (0, h // 2))
    else:
        bg = cover(Image.open(BASE / spec["bg"]), w, h)
    if spec.get("blur"):  # busy backgrounds (logos, posters) stop fighting the words
        bg = bg.filter(ImageFilter.GaussianBlur(spec["blur"]))
    canvas = vignette(grade(bg)).convert("RGBA")
    accent = spec.get("accent", "#ff4fa3")
    if spec.get("bg2"):  # bright divider for split screens
        d = ImageDraw.Draw(canvas)
        d.rectangle([w // 2 - 5, 0, w // 2 + 5, h] if w > h else [0, h // 2 - 5, w, h // 2 + 5], fill=accent)
    for c in spec.get("cutouts", []):
        landscape = w > h
        paste_cutout(canvas, c["src"], c.get("x16", c["x"]) if landscape else c["x"], c.get("y", 1.0),
                     c.get("h16", c["h"]) if landscape else c["h"], accent)
    text(canvas, spec["words"], accent, int(min(w, h) * 0.2))
    if spec.get("badge"):
        d = ImageDraw.Draw(canvas)
        f = ImageFont.truetype(str(FONTS / "BebasNeue-Regular.ttf"), int(min(w, h) * 0.06))
        tw = d.textlength(spec["badge"], font=f)
        pad = int(f.size * 0.3)
        x0, y0 = w - tw - pad * 3, h - f.size - pad * 3
        d.rounded_rectangle([x0, y0, x0 + tw + pad * 2, y0 + f.size + pad], radius=pad, fill=accent)
        d.text((x0 + pad, y0 + pad * 0.3), spec["badge"], font=f, fill=(0, 0, 0))
    return grain(canvas.convert("RGB"))


slug = sys.argv[1]
folder = ROOT / "projects" / slug
spec = json.loads((folder / "thumb.json").read_text("utf8"))
build(spec, 1080, 1920).save(folder / "thumbnail.jpg", quality=92)
build(spec, 1280, 720).save(folder / "thumbnail-16x9.jpg", quality=92)
print("thumbnails ->", folder.name)
