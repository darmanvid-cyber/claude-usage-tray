"""Generate infographic images for the README (docs/).

Run from the project root:  python scripts/make_docs.py
Output: docs/hero.png, docs/states.png, docs/how-it-works.png
"""
from __future__ import annotations

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from claude_usage_tray import config, dashboard as db, icon as ic  # noqa: E402
from claude_usage_tray.status import Quota, Status  # noqa: E402

DOCS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
os.makedirs(DOCS, exist_ok=True)

BG_TOP = (10, 14, 27)
BG_BOT = (19, 26, 47)
TXT = (236, 240, 249)
SUB = (138, 151, 179)
CARD = (24, 32, 55)
GREEN = (34, 197, 94)
ORANGE = (245, 158, 11)
RED = (239, 68, 68)
ACCENT = (74, 158, 255)

CFG = config.load()


def font(px, weight="regular"):
    table = {
        "regular": ("segoeui.ttf", "LeelawUI.ttf", "arial.ttf"),
        "semibold": ("seguisb.ttf", "segoeuib.ttf", "LeelaUIb.ttf", "arialbd.ttf"),
        "bold": ("segoeuib.ttf", "LeelaUIb.ttf", "arialbd.ttf"),
        "light": ("segoeuil.ttf", "segoeui.ttf", "arial.ttf"),
    }[weight]
    for n in table:
        try:
            return ImageFont.truetype(n, px)
        except OSError:
            continue
    return ImageFont.load_default()


def vgrad(w, h, top=BG_TOP, bot=BG_BOT):
    im = Image.new("RGB", (w, h), top)
    px = im.load()
    for y in range(h):
        t = y / max(1, h - 1)
        c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = c
    return im.convert("RGBA")


def text(d, xy, s, f, fill, anchor="la"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def shadow_card(base, card, xy, radius=28, blur=30, alpha=150):
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    x, y = xy
    sd.rounded_rectangle([x + 10, y + 18, x + card.width + 10, y + card.height + 18],
                         radius, fill=(0, 0, 0, alpha))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    # rounded corners for the card
    mask = Image.new("L", card.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, card.width, card.height], radius, fill=255)
    base.paste(card, xy, mask)


def dash(rem, sel="five_hour"):
    color = "green" if rem > 50 else ("orange" if rem > 20 else "red")
    q = [Quota("five_hour", "5 hours", 100 - rem, rem, "2026-07-11T20:00:00+00:00"),
         Quota("seven_day", "Weekly", 9, 91, "2026-07-17T00:00:00+00:00")]
    img, _ = db.render(Status(color, rem, "five_hour", q), CFG, sel)
    return img.convert("RGBA")


def tray_icon(rem):
    color = "green" if rem > 50 else ("orange" if rem > 20 else "red")
    q = [Quota("five_hour", "5 hours", 100 - rem, rem, None)]
    return ic.render(Status(color, rem, "five_hour", q), CFG).convert("RGBA")


# ---------- HERO ----------
def make_hero():
    W, Hh = 1200, 620
    img = vgrad(W, Hh)
    d = ImageDraw.Draw(img)
    # glow in the right corner
    g = Image.new("RGBA", (W, Hh), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([W - 520, -160, W + 120, 420], fill=ACCENT + (46,))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(120)))
    d = ImageDraw.Draw(img)

    # dashboard card on the right
    card = dash(76)
    scale = 500 / card.height
    card = card.resize((int(card.width * scale), 500), Image.LANCZOS)
    shadow_card(img, card, (W - card.width - 90, (Hh - card.height) // 2))

    # text on the left
    lx = 80
    text(d, (lx, 120), "Claude Usage Tray", font(58, "bold"), TXT)
    text(d, (lx, 196), "Monitor your Claude Code token usage", font(26, "regular"), SUB)
    text(d, (lx, 232), "from the Windows system tray.", font(26, "regular"), SUB)

    feats = [
        (GREEN, "Live 5-hour and weekly quota, straight from Claude Code"),
        (ORANGE, "Tray icon changes colour as your quota runs down"),
        (ACCENT, "Elegant dashboard with a circular usage gauge"),
        (TXT, "Portable EXE or one-click installer. Free and open source."),
    ]
    y = 320
    for c, tx in feats:
        d.ellipse([lx, y + 7, lx + 14, y + 21], fill=c)
        text(d, (lx + 28, y), tx, font(21, "regular"), TXT)
        y += 46

    text(d, (lx, Hh - 70), "MIT Licensed  ·  github.com/ksmaster03/claude-usage-tray",
         font(18, "semibold"), SUB)
    img.convert("RGB").save(os.path.join(DOCS, "hero.png"))


# ---------- STATES ----------
def make_states():
    W, Hh = 1100, 460
    img = vgrad(W, Hh)
    d = ImageDraw.Draw(img)
    text(d, (W // 2, 44), "Colour tells you the story at a glance", font(30, "bold"), TXT, anchor="ma")
    text(d, (W // 2, 88), "The tray icon is coloured by how much quota you have LEFT",
         font(19, "regular"), SUB, anchor="ma")

    cols = [
        (GREEN, tray_icon(78), "Healthy", "More than 50% left", "Work freely"),
        (ORANGE, tray_icon(42), "Low", "50% or less left", "Start pacing yourself"),
        (RED, tray_icon(12), "Critical", "20% or less left", "Icon blinks + popup alert"),
    ]
    cw, gap = 320, 40
    x0 = (W - (cw * 3 + gap * 2)) // 2
    for i, (c, ico, title, sub1, sub2) in enumerate(cols):
        x = x0 + i * (cw + gap)
        d.rounded_rectangle([x, 150, x + cw, 410], 24, fill=CARD)
        ico = ico.resize((104, 104), Image.LANCZOS)
        img.paste(ico, (x + (cw - 104) // 2, 176), ico)
        text(d, (x + cw // 2, 300), title, font(26, "bold"), c, anchor="ma")
        text(d, (x + cw // 2, 340), sub1, font(18, "semibold"), TXT, anchor="ma")
        text(d, (x + cw // 2, 368), sub2, font(16, "regular"), SUB, anchor="ma")
    img.convert("RGB").save(os.path.join(DOCS, "states.png"))


# ---------- HOW IT WORKS ----------
def make_flow():
    W, Hh = 1200, 380
    img = vgrad(W, Hh)
    d = ImageDraw.Draw(img)
    text(d, (W // 2, 40), "How it works", font(30, "bold"), TXT, anchor="ma")

    steps = [
        ("1", "You log in", "Official Claude Code\nlogin (one time)"),
        ("2", "Token on disk", "Claude Code stores it in\n~/.claude/.credentials.json"),
        ("3", "App reads usage", "Queries api.anthropic.com\n/api/oauth/usage (read only)"),
        ("4", "You see it", "Tray icon colour +\ndashboard gauge update"),
    ]
    bw, bh, gap = 250, 150, 40
    x0 = (W - (bw * 4 + gap * 3)) // 2
    y = 150
    for i, (num, title, body) in enumerate(steps):
        x = x0 + i * (bw + gap)
        d.rounded_rectangle([x, y, x + bw, y + bh], 22, fill=CARD)
        d.ellipse([x + 20, y + 20, x + 56, y + 56], fill=ACCENT)
        text(d, (x + 38, y + 38), num, font(22, "bold"), (255, 255, 255), anchor="mm")
        text(d, (x + 74, y + 26), title, font(21, "semibold"), TXT)
        text(d, (x + 24, y + 74), body, font(16, "regular"), SUB)
        if i < 3:
            ax = x + bw + gap // 2
            d.line([ax - 12, y + bh // 2, ax + 12, y + bh // 2], fill=SUB, width=3)
            d.polygon([(ax + 12, y + bh // 2 - 7), (ax + 24, y + bh // 2),
                       (ax + 12, y + bh // 2 + 7)], fill=SUB)
    text(d, (W // 2, y + bh + 34),
         "Your token never leaves your PC. The app only reads it locally to show your own usage.",
         font(17, "regular"), SUB, anchor="ma")
    img.convert("RGB").save(os.path.join(DOCS, "how-it-works.png"))


# ---------- WIDGET (light theme) ----------
def make_widget():
    from claude_usage_tray import widget as wg
    q = [Quota("five_hour", "5 hours", 12, 88, "2026-07-11T20:48:00+00:00"),
         Quota("seven_day", "Weekly", 10, 90, "2026-07-13T12:59:00+00:00")]
    card, _ = wg.render(Status("green", 88, "five_hour", q), CFG, "Max (20×)", "23:31")
    W2, H2 = 460, 320
    bg = vgrad(W2, H2, (232, 236, 244), (214, 221, 234))  # soft light backdrop
    x = (W2 - card.width) // 2
    y = (H2 - card.height) // 2
    bg.alpha_composite(card, (x, y))
    bg.convert("RGB").save(os.path.join(DOCS, "widget.png"))


if __name__ == "__main__":
    make_hero()
    make_states()
    make_flow()
    make_widget()
    print("wrote:", os.listdir(DOCS))
