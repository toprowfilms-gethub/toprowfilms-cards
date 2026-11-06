"""Top Row Films production title card generator (1080x1350, 4:5).

Usage:
  python3 make_card.py out.png --title "Film Title" --director "Jane Doe" \
      --genre "Drama" --location "Newark, NJ" --status "Shooting now" \
      [--logline "One-line premise."] [--index "1/3"] [--cover art.jpg]

--cover is optional. Only pass artwork you made or have permission to use.
Without it, the cover-art frame shows a branded placeholder.
"""
import argparse
import sys
import glob
import os

from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
W, H = 1080, 1350
M = 72

BG = (26, 13, 18)          # matches the logo background
PANEL = (42, 22, 29)
INK = (244, 234, 216)      # cream
GOLD = (226, 176, 74)
MUTED = (176, 160, 150)
RULE = (70, 48, 50)
PILL_TEXT = (40, 18, 22)


def font(weight, size):
    names = {
        "black": ["InterDisplay-Black.otf", "Inter-Black.otf", "InterDisplay-ExtraBold.otf", "Inter-Bold.otf"],
        "bold": ["InterDisplay-Bold.otf", "Inter-Bold.otf"],
        "semi": ["Inter-SemiBold.otf", "Inter-Medium.otf"],
        "reg": ["Inter-Regular.otf", "Inter-Medium.otf"],
    }[weight]
    for n in names:
        hits = glob.glob(f"/usr/share/fonts/**/{n}", recursive=True)
        if hits:
            return ImageFont.truetype(hits[0], size)
    fb = "DejaVuSans-Bold.ttf" if weight != "reg" else "DejaVuSans.ttf"
    hits = glob.glob(f"/usr/share/fonts/**/{fb}", recursive=True)
    return ImageFont.truetype(hits[0], size) if hits else ImageFont.load_default()


def wrap_px(d, text, f, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fit(d, text, weight, max_w, max_h, max_lines, start, stop, leading=1.04):
    for size in range(start, stop - 1, -4):
        f = font(weight, size)
        lines = wrap_px(d, text, f, max_w)
        if (len(lines) <= max_lines and all(d.textlength(l, font=f) <= max_w for l in lines)
                and len(lines) * int(size * leading) <= max_h):
            return f, lines, size
    f = font(weight, stop)
    return f, wrap_px(d, text, f, max_w)[:max_lines], stop


def paste_asset(img, name, box_w, box_h, x, y, opacity=1.0, center=False):
    path = os.path.join(HERE, "assets", name)
    if not os.path.exists(path):
        return 0
    a = Image.open(path).convert("RGBA")
    a.thumbnail((box_w, box_h), Image.LANCZOS)
    if opacity < 1:
        alpha = a.getchannel("A").point(lambda v: int(v * opacity))
        a.putalpha(alpha)
    if center:
        x += (box_w - a.width) // 2
        y += (box_h - a.height) // 2
    img.paste(a, (x, y), a)
    return a.height


def cover_frame(img, d, x, y, w, h, cover, title="", genre="", art=True):
    if cover and os.path.exists(cover):
        img.paste(ImageOps.fit(Image.open(cover).convert("RGB"), (w, h), Image.LANCZOS), (x, y))
    elif art:
        from cover_art import make_cover
        img.paste(make_cover(title, genre, w, h), (x, y))
        cf = font("semi", 18)
        label = "ARTWORK: TOP ROW FILMS"
        lw = d.textlength(label, font=cf)
        d.rectangle((x + w - lw - 24, y + h - 36, x + w, y + h), fill=BG)
        d.text((x + w - lw - 12, y + h - 30), label, font=cf, fill=MUTED)
    else:
        d.rectangle((x, y, x + w, y + h), fill=PANEL)
        iw = int(w * 0.46)
        ih = paste_asset(img, "icon.png", iw, iw, x + (w - iw) // 2, y + (h - iw) // 2, opacity=0.5)
    d.rectangle((x, y, x + w, y + h), outline=GOLD, width=3)


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
    p.add_argument("--cover", default="")
    p.add_argument("--art", action="store_true", help="fill the frame with generated Top Row Films artwork")
    a = p.parse_args()

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Header: logo + index
    paste_asset(img, "logo.png", 470, 130, M - 6, 54)
    if a.index:
        f = font("semi", 28)
        d.text((W - M - d.textlength(a.index, font=f), 70), a.index, font=f, fill=MUTED)
    d.line((M, 214, W - M, 214), fill=RULE, width=2)

    # Cover-art frame (2:3) on the left
    top = 258
    cw, ch = 380, 570
    cover_frame(img, d, M, top, cw, ch, a.cover, a.title, a.genre, a.art)

    # Right column: status, title, director
    rx = M + cw + 44
    rw = W - M - rx
    y = top
    if a.status:
        sf = font("bold", 26)
        s = a.status.upper()
        tw = min(d.textlength(s, font=sf), rw - 48)
        d.rounded_rectangle((rx, y, rx + tw + 48, y + 54), radius=27, fill=GOLD)
        d.text((rx + 24, y + 12), s, font=sf, fill=PILL_TEXT)
        y += 86

    dlines, dsize, df = [], 0, None
    if a.director:
        df, dlines, dsize = fit(d, f"Dir. {a.director}", "semi", rw, 100, 2, 38, 26, 1.25)
    dir_h = (22 + len(dlines) * int(dsize * 1.25)) if dlines else 0
    tf, tlines, tsize = fit(d, a.title.upper(), "black", rw, top + ch - y - dir_h, 5, 104, 40)
    lh = int(tsize * 1.04)
    for line in tlines:
        d.text((rx, y), line, font=tf, fill=INK)
        y += lh
    y += 22
    if dlines:
        for line in dlines:
            d.text((rx, y), line, font=df, fill=GOLD)
            y += int(dsize * 1.25)

    # Logline, full width under the frame
    y = top + ch + 40
    if a.logline:
        lf, llines, lsize = fit(d, a.logline, "reg", W - 2 * M, 100, 2, 36, 28, 1.35)
        for line in llines:
            d.text((M, y), line, font=lf, fill=MUTED)
            y += int(lsize * 1.35)

    # Info rows: genre + shooting side by side
    iy = 1090
    d.line((M, iy, W - M, iy), fill=RULE, width=2)
    cols = [(k, v) for k, v in (("GENRE", a.genre), ("SHOOTING", a.location)) if v]
    colw = (W - 2 * M) // max(1, len(cols))
    for i, (k, v) in enumerate(cols):
        cx = M + i * colw
        d.text((cx, iy + 22), k, font=font("semi", 24), fill=GOLD)
        vf, vlines, vsize = fit(d, v, "bold", colw - 24, 100, 2, 40, 26, 1.15)
        vy = iy + 56
        for line in vlines:
            d.text((cx, vy), line, font=vf, fill=INK)
            vy += int(vsize * 1.15)

    # Footer
    d.line((M, H - 110, W - M, H - 110), fill=RULE, width=2)
    ff = font("semi", 28)
    d.text((M, H - 82), "toprowfilms.com", font=ff, fill=MUTED)
    tag = "@toprowfilms"
    d.text((W - M - d.textlength(tag, font=ff), H - 82), tag, font=ff, fill=GOLD)

    img.save(a.out, quality=92) if a.out.lower().endswith((".jpg", ".jpeg")) else img.save(a.out, optimize=True)
    print(os.path.abspath(a.out))


if __name__ == "__main__":
    main()
