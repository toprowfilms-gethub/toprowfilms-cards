"""Top Row Films vertical (9:16) motion-graphics title video with glitter and original music.

Usage:
  python3 make_video.py out.mp4 --title "Find Me in the Sky" --director "Palomino Shonberg" \
      --genre "Family drama" --location "Central NJ" --status "Shooting now" \
      --logline "A family fights to stay whole as a mother's illness erases who she is."
"""
import argparse
import math
import os
import random
import subprocess
import sys
import tempfile
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_card import font, fit, BG, INK, GOLD, MUTED, RULE, PILL_TEXT  # noqa: E402

W, H = 1080, 1920
FPS = 30
DUR = 12.0
M = 84


# ---------- easing ----------
def clamp(x):
    return max(0.0, min(1.0, x))


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_back(t):
    t = clamp(t)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def window(t, start, length):
    return clamp((t - start) / length)


# ---------- static layers ----------
def layer():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


def build_layers(a):
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    L = {}

    # logo
    lg = layer()
    logo = Image.open(os.path.join(HERE, "assets", "logo.png")).convert("RGBA")
    logo.thumbnail((560, 160), Image.LANCZOS)
    lg.paste(logo, ((W - logo.width) // 2, 150), logo)
    ImageDraw.Draw(lg).line((M, 360, W - M, 360), fill=RULE + (255,), width=2)
    L["logo"] = lg

    y = 470
    # status pill
    if a.status:
        pl = layer()
        d = ImageDraw.Draw(pl)
        sf = font("bold", 34)
        s = a.status.upper()
        tw = d.textlength(s, font=sf)
        pw, ph = tw + 64, 72
        x0 = (W - pw) / 2
        d.rounded_rectangle((x0, y, x0 + pw, y + ph), radius=36, fill=GOLD + (255,))
        d.text((x0 + 32, y + 16), s, font=sf, fill=PILL_TEXT)
        L["pill"] = (pl, (W / 2, y + ph / 2))
        y += 130

    # title lines (centered), one layer per line
    bw = W - 2 * M
    tf, tlines, tsize = fit(probe, a.title.upper(), "black", bw, 560, 4, 170, 64)
    L["title"] = []
    lh = int(tsize * 1.02)
    for line in tlines:
        tl = layer()
        d = ImageDraw.Draw(tl)
        lw = d.textlength(line, font=tf)
        d.text(((W - lw) / 2, y), line, font=tf, fill=INK)
        L["title"].append(tl)
        y += lh
    y += 40

    if a.director:
        dl = layer()
        d = ImageDraw.Draw(dl)
        df, dlines, dsize = fit(probe, f"Dir. {a.director}", "semi", bw, 140, 2, 54, 34, 1.2)
        for line in dlines:
            lw = d.textlength(line, font=df)
            d.text(((W - lw) / 2, y), line, font=df, fill=GOLD)
            y += int(dsize * 1.2)
        L["director"] = dl
        y += 36

    if a.logline:
        ll = layer()
        d = ImageDraw.Draw(ll)
        lf, llines, lsize = fit(probe, a.logline, "reg", bw - 40, 200, 3, 44, 32, 1.35)
        for line in llines:
            lw = d.textlength(line, font=lf)
            d.text(((W - lw) / 2, y), line, font=lf, fill=MUTED)
            y += int(lsize * 1.35)
        L["logline"] = ll

    # info row
    il = layer()
    d = ImageDraw.Draw(il)
    iy = 1500
    d.line((M, iy, W - M, iy), fill=RULE + (255,), width=2)
    cols = [(k, v) for k, v in (("GENRE", a.genre), ("SHOOTING", a.location)) if v]
    colw = (W - 2 * M) // max(1, len(cols))
    for i, (k, v) in enumerate(cols):
        cx = M + i * colw + colw / 2
        kf = font("semi", 28)
        d.text((cx - d.textlength(k, font=kf) / 2, iy + 30), k, font=kf, fill=GOLD)
        vf, vlines, vsize = fit(d, v, "bold", colw - 30, 120, 2, 48, 30, 1.15)
        vy = iy + 72
        for line in vlines:
            d.text((cx - d.textlength(line, font=vf) / 2, vy), line, font=vf, fill=INK)
            vy += int(vsize * 1.15)
    L["info"] = il

    # footer
    fl = layer()
    d = ImageDraw.Draw(fl)
    d.line((M, 1740, W - M, 1740), fill=RULE + (255,), width=2)
    ff = font("semi", 32)
    d.text((M, 1776), "toprowfilms.com", font=ff, fill=MUTED)
    tag = "@toprowfilms"
    d.text((W - M - d.textlength(tag, font=ff), 1776), tag, font=ff, fill=GOLD)
    L["footer"] = fl

    # end card
    el = layer()
    d = ImageDraw.Draw(el)
    big = Image.open(os.path.join(HERE, "assets", "logo.png")).convert("RGBA")
    big.thumbnail((820, 260), Image.LANCZOS)
    el.paste(big, ((W - big.width) // 2, 780), big)
    ef = font("semi", 40)
    for i, txt in enumerate(["NJ / NY Production Watch", "@toprowfilms"]):
        col = MUTED if i == 0 else GOLD
        d.text(((W - d.textlength(txt, font=ef)) / 2, 1110 + i * 64), txt, font=ef, fill=col)
    L["end"] = el
    return L


# ---------- background ----------
def make_background():
    base = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-100, -700, W + 100, 520), fill=(80, 50, 18))
    gd.ellipse((-300, 1500, W + 300, H + 700), fill=(50, 10, 22))
    glow = glow.filter(ImageFilter.GaussianBlur(220))
    return np.clip(np.asarray(base, np.float32) + np.asarray(glow, np.float32) * 0.45, 0, 255)


def spotlight(t):
    """Soft moving light sweep; returns float array to add."""
    sl = Image.new("L", (W // 4, H // 4), 0)
    d = ImageDraw.Draw(sl)
    cx = W / 8 + math.sin(t * 0.6) * W / 10
    d.ellipse((cx - 120, 120, cx + 120, 420), fill=70)
    sl = sl.filter(ImageFilter.GaussianBlur(40)).resize((W, H), Image.BILINEAR)
    a = np.asarray(sl, np.float32)[..., None] / 255.0
    return a * np.array([255, 215, 140], np.float32) * 0.35


# ---------- glitter ----------
class Glitter:
    def __init__(self, n, seed):
        r = random.Random(seed)
        self.p = []
        for _ in range(n):
            self.p.append(dict(
                x=r.uniform(0, W), y=r.uniform(-H, H), vy=r.uniform(40, 140), vx=r.uniform(-20, 20),
                size=r.choice([2, 2, 3, 3, 4, 5, 7]), phase=r.uniform(0, 6.28), speed=r.uniform(3, 9),
                hue=r.choice([(255, 214, 120), (246, 230, 190), (226, 176, 74), (255, 245, 220)]),
            ))
        self.burst = []
        for _ in range(140):
            ang = r.uniform(0, 6.28)
            sp = r.uniform(300, 1100)
            self.burst.append(dict(vx=math.cos(ang) * sp, vy=math.sin(ang) * sp - 200,
                                   size=r.choice([2, 3, 4, 6]), phase=r.uniform(0, 6.28),
                                   hue=r.choice([(255, 214, 120), (255, 245, 220), (226, 176, 74)])))

    def draw(self, t, burst_t=None, burst_origin=(W / 2, H / 2)):
        img = Image.new("RGB", (W, H), (0, 0, 0))
        d = ImageDraw.Draw(img)
        items = []
        for p in self.p:
            y = (p["y"] + p["vy"] * t) % (H + 40) - 20
            x = (p["x"] + p["vx"] * t + math.sin(t + p["phase"]) * 14) % W
            tw = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * p["speed"] + p["phase"])) ** 3
            items.append((x, y, p["size"], tw, p["hue"]))
        if burst_t is not None and burst_t >= 0:
            bx, by = burst_origin
            fade = clamp(1 - burst_t / 1.6)
            for b in self.burst:
                x = bx + b["vx"] * burst_t
                y = by + b["vy"] * burst_t + 500 * burst_t ** 2
                tw = fade * (0.5 + 0.5 * math.sin(burst_t * 12 + b["phase"]))
                items.append((x, y, b["size"], tw, b["hue"]))
        for x, y, s, tw, hue in items:
            c = tuple(int(v * tw) for v in hue)
            if s >= 5:  # four-point sparkle
                d.line((x - s * 2.2, y, x + s * 2.2, y), fill=c, width=2)
                d.line((x, y - s * 2.2, x, y + s * 2.2), fill=c, width=2)
            d.ellipse((x - s / 2, y - s / 2, x + s / 2, y + s / 2), fill=c)
        glow = img.filter(ImageFilter.GaussianBlur(4))
        return np.asarray(img, np.float32) + np.asarray(glow, np.float32) * 1.4


# ---------- compositing ----------
def paste(frame, lay, alpha, dx=0, dy=0, scale=1.0, center=None):
    if alpha <= 0:
        return
    src = lay
    if scale != 1.0 and center is not None:
        cx, cy = center
        sw, sh = int(W * scale), int(H * scale)
        src = lay.resize((sw, sh), Image.BILINEAR)
        dx += int(cx - cx * scale)
        dy += int(cy - cy * scale)
    if alpha < 1:
        src = src.copy()
        src.putalpha(src.getchannel("A").point(lambda v: int(v * alpha)))
    frame.paste(src, (int(dx), int(dy)), src)


def render_frames(a, outdir):
    L = build_layers(a)
    bg = make_background()
    glitter = Glitter(260, hash(a.title) & 0xFFFF)
    n = int(DUR * FPS)
    for i in range(n):
        t = i / FPS
        base = bg + spotlight(t)
        burst_t = t - 9.6 if t >= 9.6 else None
        base = base + glitter.draw(t, burst_t, (W / 2, 900))
        intro = clamp(t / 0.8)
        base = base * (0.15 + 0.85 * intro)
        frame = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")

        out_fade = 1 - window(t, 9.5, 0.6)          # card content fades out
        e = ease_out(window(t, 0.3, 0.9))
        paste(frame, L["logo"], e * out_fade, dy=-40 * (1 - e))
        if "pill" in L:
            lay, c = L["pill"]
            p = window(t, 1.1, 0.5)
            paste(frame, lay, clamp(p * 3) * out_fade, scale=max(0.01, ease_back(p)), center=c)
        for k, tl in enumerate(L["title"]):
            p = ease_out(window(t, 1.6 + k * 0.35, 0.7))
            paste(frame, tl, p * out_fade, dy=80 * (1 - p))
        if "director" in L:
            p = ease_out(window(t, 1.6 + len(L["title"]) * 0.35 + 0.4, 0.6))
            paste(frame, L["director"], p * out_fade, dx=0, dy=30 * (1 - p))
        if "logline" in L:
            p = ease_out(window(t, 3.6, 0.8))
            paste(frame, L["logline"], p * out_fade)
        p = ease_out(window(t, 4.3, 0.8))
        paste(frame, L["info"], p * out_fade, dy=120 * (1 - p))
        p = ease_out(window(t, 4.8, 0.6))
        paste(frame, L["footer"], p * out_fade)
        p = ease_out(window(t, 10.0, 0.8))
        paste(frame, L["end"], p * (1 - window(t, 11.5, 0.5)), scale=0.92 + 0.08 * p, center=(W / 2, 1000))

        frame.convert("RGB").save(os.path.join(outdir, f"f{i:04d}.png"), compress_level=1)


# ---------- original music ----------
SR = 44100


def note(freq, dur, kind="pad"):
    t = np.arange(int(SR * dur)) / SR
    if kind == "pad":
        sig = sum(np.sin(2 * np.pi * freq * h * t + h) / h ** 1.6 for h in range(1, 7))
        sig += 0.5 * np.sin(2 * np.pi * freq * 1.003 * t)
        env = np.minimum(1, t / 0.9) * np.minimum(1, (dur - t) / 0.9)
    elif kind == "pluck":
        sig = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2 * t) + 0.12 * np.sin(2 * np.pi * freq * 3 * t)
        env = np.exp(-t * 3.2) * np.minimum(1, t / 0.005)
    elif kind == "chime":
        sig = np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(2 * np.pi * freq * 2.76 * t) + 0.2 * np.sin(2 * np.pi * freq * 5.4 * t)
        env = np.exp(-t * 2.2) * np.minimum(1, t / 0.003)
    else:  # sub pulse
        sig = np.sin(2 * np.pi * freq * t * (1 + 0.6 * np.exp(-t * 30)))
        env = np.exp(-t * 7)
    return sig * env


def hz(n):
    return 440 * 2 ** ((n - 69) / 12)


def make_music(path):
    total = np.zeros(int(SR * (DUR + 0.5)))

    def add(sig, start, gain):
        s = int(start * SR)
        e = min(len(total), s + len(sig))
        total[s:e] += sig[: e - s] * gain

    # Am - F - C - G, 3s each
    chords = [[57, 60, 64], [53, 57, 60], [48, 55, 64], [55, 59, 62]]
    for ci, ch in enumerate(chords):
        st = ci * 3.0
        for n in ch:
            add(note(hz(n), 3.4, "pad"), st, 0.05)
        add(note(hz(ch[0] - 12), 3.4, "pad"), st, 0.05)
        # arpeggio
        arp = ch + [ch[0] + 12, ch[1] + 12, ch[2] + 12]
        for k in range(8):
            if st + k * 0.375 < 1.0:
                continue
            add(note(hz(arp[(k * 3) % len(arp)] + 12), 1.4, "pluck"), st + k * 0.375, 0.07)
        # pulse
        for k in range(4):
            if st + k * 0.75 >= 1.5:
                add(note(55, 0.5, "sub"), st + k * 0.75, 0.22)
    # glitter chimes
    r = random.Random(7)
    for _ in range(26):
        add(note(hz(r.choice([76, 79, 81, 84, 88, 91])), 1.6, "chime"), r.uniform(0.2, 9.4), 0.035)
    # burst shimmer at 9.6s
    for k, n in enumerate([84, 88, 91, 96, 100]):
        add(note(hz(n), 2.0, "chime"), 9.6 + k * 0.06, 0.07)
    # simple reverb-ish echo
    d = int(0.23 * SR)
    wet = np.zeros_like(total)
    wet[d:] += total[:-d] * 0.35
    wet[2 * d:] += total[:-2 * d] * 0.18
    total = total + wet
    # master fade
    t = np.arange(len(total)) / SR
    total *= np.minimum(1, t / 0.6) * np.clip((DUR + 0.2 - t) / 1.2, 0, 1)
    total = total / (np.max(np.abs(total)) + 1e-9) * 0.85
    pcm = (total * 32767).astype(np.int16)
    stereo = np.stack([pcm, np.roll(pcm, 220)], axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(stereo.tobytes())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("out")
    for k in ("title", "director", "genre", "location", "status", "logline"):
        p.add_argument(f"--{k}", default="", required=(k == "title"))
    a = p.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        render_frames(a, tmp)
        wav = os.path.join(tmp, "music.wav")
        make_music(wav)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "f%04d.png"),
                        "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out], check=True)
    print(os.path.abspath(a.out))


if __name__ == "__main__":
    main()
