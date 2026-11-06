"""Top Row Films "NJ/NY Production Watch" title card generator.

Usage:
  python3 make_card.py out.png --title "Film Title" --director "Jane Doe" \
      --genre "Drama" --location "Newark, NJ" --status "Shooting now" \
      [--logline "One-line premise."] [--index "1/3"]
"""
import argparse
import glob
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1350  # 4:5 portrait, works for Instagram, Facebook, LinkedIn, TikTok photo
BG = (12, 12, 14)
INK = (245, 242, 235)
MUTED = (160, 156, 148)
ACCENT = (232, 176, 52)  # marquee gold
ACCENT_DARK = (30, 24, 10)


def font(weight, size):
    candidates = {
        "black": ["InterDisplay-Black.otf", "Inter-Black.otf", "InterDisplay-ExtraBold.otf", "Inter-Bold.otf"],
        "bold": ["InterDisplay-Bold.otf", "Inter-Bold.otf"],
        "semi": ["Inter-SemiBold.otf", "Inter-Medium.otf"],
        "reg": ["Inter-Regular.otf", "Inter-Medium.otf"],
    }[weight]
    for name in candidates:
        hits = glob.glob(f"/usr/share/fonts/**/{name}", recursive=True)
        if hits:
            return ImageFont.truetype(hits[0], size)
    fallback = "DejaVuSans-Bold.ttf" if weight in ("black", "bold", "semi") else "DejaVuSans.ttf"
    hits = glob.glob(f"/usr/share/fonts/**/{fallback}", recursive=True)
    return ImageFont.truetype(hits[0], size) if hits else ImageFont.load_default()


def wrap_px(draw, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=f) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit_title(draw, text, max_w, max_lines=3, start=150):
    """Largest title size whose lines all fit within max_w on <= max_lines lines."""
    for size in range(start, 53, -6):
        f = font("black", size)
        lines = wrap_px(draw, text.upper(), f, max_w)
        if len(lines) <= max_lines and all(draw.textlength(l, font=f) <= max_w for l in lines):
            return f, lines, size
    f = font("black", 54)
    return f, wrap_px(draw, text.upper(), f, max_w)[:4], 54


def draw_marquee_glow(img):
    glow = Image.new("RGB", (W, H), BG)
    g = ImageDraw.Draw(glow)
    g.ellipse((-300, -520, W + 300, 420), fill=(70, 50, 14))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    return Image.blend(img, glow, 0.85)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("out")
    p.add_argument("--title", required=True)
    p.add_argument("--director", default="")
    p.add_argument("--genre", default="")
    p.add_argument("--location", default="")
    p.add_argument("--status", default="")
    p.add_argument("--logline", default="")
    p.add_argument("--index", default="")
    a = p.parse_args()

    img = Image.new("RGB", (W, H), BG)
    img = draw_marquee_glow(img)
    d = ImageDraw.Draw(img)
    M = 84

    # Header: brand + series label
    d.text((M, 86), "TOP ROW FILMS", font=font("black", 34), fill=ACCENT)
    label = "NJ / NY PRODUCTION WATCH"
    lf = font("semi", 26)
    d.text((M, 132), label, font=lf, fill=MUTED)
    if a.index:
        f = font("semi", 26)
        d.text((W - M - d.textlength(a.index, font=f), 92), a.index, font=f, fill=MUTED)
    d.line((M, 188, W - M, 188), fill=(60, 56, 50), width=2)

    # Status pill
    y = 250
    if a.status:
        sf = font("bold", 30)
        s = a.status.upper()
        tw = d.textlength(s, font=sf)
        d.rounded_rectangle((M, y, M + tw + 56, y + 62), radius=31, fill=ACCENT)
        d.text((M + 28, y + 13), s, font=sf, fill=ACCENT_DARK)
        y += 120

    # Info rows anchored to bottom (computed first so the title can shrink to fit above them)
    rows = [(k, v) for k, v in (("GENRE", a.genre), ("SHOOTING", a.location)) if v]
    by0 = H - 150 - len(rows) * 96
    limit = by0 - 48

    lgf = font("reg", 34)
    log_lines = textwrap.wrap(a.logline, width=46)[:3] if a.logline else []

    def body_height(size, n_lines):
        h = n_lines * int(size * 1.02) + 36
        if a.director:
            h += 74
        h += len(log_lines) * 48
        return h

    tf, lines, size = fit_title(d, a.title, W - 2 * M)
    while y + body_height(size, len(lines)) > limit and size > 54:
        tf, lines, size = fit_title(d, a.title, W - 2 * M, max_lines=4, start=size - 6)
    if y + body_height(size, len(lines)) > limit:
        log_lines = log_lines[:1]

    lh = int(size * 1.02)
    for line in lines:
        d.text((M, y), line, font=tf, fill=INK)
        y += lh
    y += 36

    if a.director:
        d.text((M, y), f"Dir. {a.director}", font=font("semi", 44), fill=INK)
        y += 74

    for line in log_lines:
        d.text((M, y), line, font=lgf, fill=MUTED)
        y += 48

    # Info rows
    by = by0
    kf, vf = font("semi", 24), font("bold", 40)
    for k, v in rows:
        d.line((M, by, W - M, by), fill=(60, 56, 50), width=2)
        d.text((M, by + 18), k, font=kf, fill=ACCENT)
        d.text((M, by + 46), v, font=vf, fill=INK)
        by += 96

    # Footer
    ff = font("semi", 26)
    d.text((M, H - 92), "Daily indie film news from NJ & NYC", font=ff, fill=MUTED)
    tag = "@toprowfilms"
    d.text((W - M - d.textlength(tag, font=ff), H - 92), tag, font=ff, fill=ACCENT)

    img.save(a.out, "PNG", optimize=True)
    print(os.path.abspath(a.out))


if __name__ == "__main__":
    main()
