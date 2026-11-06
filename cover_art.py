"""Original, generative cover art for Top Row Films cards.

The art is abstract and driven by genre plus a few title keywords. It is
Top Row Films' own artwork, never an imitation of a film's official poster,
and it is labelled as such on the card.
"""
import hashlib
import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageChops

PALETTES = {
    "horror":   [(14, 6, 8), (70, 10, 18), (150, 20, 32), (235, 200, 150)],
    "thriller": [(8, 12, 22), (22, 44, 78), (60, 110, 160), (230, 220, 190)],
    "drama":    [(22, 12, 10), (96, 52, 30), (196, 120, 60), (250, 226, 180)],
    "comedy":   [(30, 20, 60), (226, 176, 74), (232, 90, 70), (250, 240, 220)],
    "sci-fi":   [(6, 10, 24), (30, 30, 90), (60, 200, 220), (230, 240, 255)],
    "doc":      [(18, 18, 18), (60, 60, 60), (150, 150, 150), (240, 236, 228)],
    "romance":  [(30, 10, 22), (120, 30, 60), (220, 110, 130), (250, 230, 220)],
}


def palette_for(genre):
    g = genre.lower()
    for key, words in (
        ("horror", ["horror", "slasher", "supernatural"]),
        ("sci-fi", ["sci", "science", "fantasy"]),
        ("thriller", ["thriller", "crime", "mystery", "noir", "action"]),
        ("comedy", ["comedy", "musical", "family"]),
        ("doc", ["doc", "documentary"]),
        ("romance", ["romance", "love"]),
        ("drama", ["drama", "coming", "biopic"]),
    ):
        if any(w in g for w in words):
            return PALETTES[key], key
    return PALETTES["drama"], "drama"


def vgrad(w, h, top, bottom):
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        d.line((0, y, w, y), fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return img


def glow(w, h, cx, cy, r, color, strength=1.0):
    layer = Image.new("RGB", (w, h), (0, 0, 0))
    ImageDraw.Draw(layer).ellipse((cx - r, cy - r, cx + r, cy + r), fill=tuple(int(c * strength) for c in color))
    return layer.filter(ImageFilter.GaussianBlur(r * 0.6))


def grain(img, rng, amount=40):
    noise = Image.effect_noise(img.size, amount).convert("RGB")
    return Image.blend(img, noise, 0.05)


def motif_door(img, pal, rng):
    w, h = img.size
    d = ImageDraw.Draw(img)
    dw, dh = int(w * 0.46), int(h * 0.62)
    x0, y0 = (w - dw) // 2, int(h * 0.2)
    d.rectangle((x0 - 14, y0 - 14, x0 + dw + 14, y0 + dh), fill=pal[1])
    d.rectangle((x0, y0, x0 + dw, y0 + dh), fill=pal[0])
    # light leaking through the gap at the bottom and the crack on one side
    img.paste(ImageChops.add(img, glow(w, h, w // 2, y0 + dh + 6, int(dw * 0.6), pal[3], 0.9)), (0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle((x0, y0 + dh - 5, x0 + dw, y0 + dh + 2), fill=pal[3])
    d.rectangle((x0 + dw - 4, y0, x0 + dw + 2, y0 + dh), fill=pal[2])
    d.ellipse((x0 + int(dw * 0.12), y0 + dh // 2, x0 + int(dw * 0.12) + 16, y0 + dh // 2 + 16), fill=pal[2])
    # floor
    d.polygon([(0, y0 + dh + 2), (w, y0 + dh + 2), (w, h), (0, h)], fill=pal[0])
    beam = Image.new("L", (w, h), 0)
    ImageDraw.Draw(beam).polygon([(x0, y0 + dh), (x0 + dw, y0 + dh), (w, h), (0, h)], fill=70)
    img.paste(Image.new("RGB", (w, h), pal[3]), (0, 0), beam.filter(ImageFilter.GaussianBlur(18)))
    return img


def motif_water(img, pal, rng):
    w, h = img.size
    d = ImageDraw.Draw(img)
    horizon = int(h * 0.45)
    img.paste(ImageChops.add(img, glow(w, h, w // 2, horizon, int(w * 0.35), pal[2], 0.8)), (0, 0))
    d = ImageDraw.Draw(img)
    for i in range(26):
        y = horizon + int((i / 26) ** 1.6 * (h - horizon))
        amp = 4 + i * 0.9
        pts = [(x, y + math.sin(x / (30 + i * 3) + i) * amp) for x in range(0, w + 8, 8)]
        d.line(pts, fill=pal[1] if i % 2 else pal[2], width=2 + i // 8)
    return img


def motif_city(img, pal, rng):
    w, h = img.size
    img.paste(ImageChops.add(img, glow(w, h, w // 2, int(h * 0.55), int(w * 0.45), pal[2], 0.7)), (0, 0))
    d = ImageDraw.Draw(img)
    base = int(h * 0.78)
    x = -10
    while x < w:
        bw = rng.randint(34, 80)
        bh = rng.randint(int(h * 0.15), int(h * 0.5))
        d.rectangle((x, base - bh, x + bw, h), fill=pal[0])
        for wy in range(base - bh + 14, base - 10, 22):
            for wx in range(x + 8, x + bw - 10, 16):
                if rng.random() < 0.28:
                    d.rectangle((wx, wy, wx + 6, wy + 9), fill=pal[3])
        x += bw + rng.randint(2, 8)
    d.rectangle((0, base, w, h), fill=pal[0])
    return img


def motif_beams(img, pal, rng):
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    ox, oy = rng.randint(int(w * 0.2), int(w * 0.8)), -int(h * 0.1)
    for _ in range(rng.randint(3, 5)):
        a = rng.uniform(math.radians(60), math.radians(120))
        spread = rng.uniform(0.05, 0.12)
        L = h * 1.5
        md.polygon([(ox, oy), (ox + L * math.cos(a - spread), oy + L * math.sin(a - spread)),
                    (ox + L * math.cos(a + spread), oy + L * math.sin(a + spread))], fill=rng.randint(40, 90))
    img.paste(Image.new("RGB", (w, h), pal[3]), (0, 0), mask.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(img)
    # lone figure
    fx, fy = w // 2 + rng.randint(-40, 40), int(h * 0.8)
    d.ellipse((fx - 13, fy - 120, fx + 13, fy - 94), fill=pal[0])
    d.polygon([(fx - 22, fy - 92), (fx + 22, fy - 92), (fx + 16, fy), (fx - 16, fy)], fill=pal[0])
    d.rectangle((0, fy, w, h), fill=pal[0])
    return img


def motif_rings(img, pal, rng):
    w, h = img.size
    cx, cy = w // 2, int(h * 0.42)
    img.paste(ImageChops.add(img, glow(w, h, cx, cy, int(w * 0.3), pal[2], 0.9)), (0, 0))
    d = ImageDraw.Draw(img)
    for i in range(9, 0, -1):
        r = int(w * 0.07 * i)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=pal[3] if i % 3 == 0 else pal[2], width=2)
    d.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), fill=pal[3])
    return img


KEYWORD_MOTIFS = [
    (("door", "room", "house", "home", "inside", "basement"), motif_door),
    (("river", "water", "sea", "ocean", "lake", "rain", "flood", "drown", "passaic", "hudson"), motif_water),
    (("block", "city", "street", "newark", "brooklyn", "bronx", "harlem", "jersey", "york", "town"), motif_city),
]
GENRE_MOTIFS = {"horror": motif_beams, "thriller": motif_beams, "drama": motif_city,
                "comedy": motif_rings, "sci-fi": motif_rings, "doc": motif_city, "romance": motif_rings}


def make_cover(title, genre, w, h):
    seed = int(hashlib.md5(title.lower().encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)
    pal, key = palette_for(genre)
    img = vgrad(w, h, pal[0], tuple(min(255, c + 16) for c in pal[1]))
    words = title.lower().replace("'", " ")
    motif = next((fn for kws, fn in KEYWORD_MOTIFS if any(k in words for k in kws)), GENRE_MOTIFS[key])
    img = motif(img, pal, rng)
    # vignette + grain for a film look
    vig = Image.new("L", (w, h), 0)
    ImageDraw.Draw(vig).ellipse((-w * 0.35, -h * 0.25, w * 1.35, h * 1.25), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(w * 0.12))
    dark = img.point(lambda v: int(v * 0.55))
    img = Image.composite(img, dark, vig)
    return grain(img, rng)
