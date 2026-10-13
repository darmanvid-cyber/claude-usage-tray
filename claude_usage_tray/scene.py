"""Animated Bigotes scene for the floating widget: works at the laptop, plays with a ball, sleeps.

Drawing only. The widget calls `render(...)` a few times per second with a monotonic clock.
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFont

from . import kenji
from .status import RED, Status

W, H = 292, 108          # scene size in widget pixels
SCALE = 3                # sprite pixel -> screen pixels
GROUND = H - 8
DOG_X = 10
SLEEP_AFTER = 60.0       # seconds without a Claude session writing before Bigotes falls asleep

PANEL = (243, 245, 249, 255)
LINE = (225, 228, 235, 255)
BALL = (232, 78, 64, 255)
BALL_HI = (255, 170, 150, 255)
ZZ = (139, 146, 159, 255)

_sleep_cache: dict[int, Image.Image] = {}


def _sleep_frame(breath: int) -> Image.Image:
    """Lying dog built from the standing head + a drawn body, eyes closed. breath = 0/1 chest rise."""
    if breath in _sleep_cache:
        return _sleep_cache[breath]
    pal = {k: kenji._hex(v) for k, v in kenji._data()["palette"].items()}
    cols, rows = 58, 32
    img = Image.new("RGBA", (cols, rows), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rise = breath
    # body: loaf ellipse with outline, lighter belly line, little tail curl on the left
    d.ellipse([4, 15 - rise, 46, 31], fill=pal["K"])
    d.ellipse([5, 16 - rise, 45, 30], fill=pal["G"])
    d.ellipse([9, 24, 41, 30], fill=pal["M"])
    d.arc([8, 18 - rise, 40, 29], 200, 330, fill=pal["D"])
    d.ellipse([1, 22, 9, 30], fill=pal["K"])
    d.ellipse([2, 23, 8, 29], fill=pal["G"])
    # head from the standing frame (columns 32-50, rows 0-21), lowered onto the body front
    head = kenji._compose("standTail0").crop((32, 0, 51, 22))
    hp = head.load()
    for x, y in kenji._data()["points"]["standEyes"]:          # close the eyes
        hp[x - 32, y] = pal["G"]
        hp[x - 32, y + 1] = pal["K"]
    img.alpha_composite(head, (28, 9 - rise))
    # front paws under the chin
    d.ellipse([34, 27, 52, 31], fill=pal["K"])
    d.ellipse([35, 28, 51, 30], fill=pal["L"])
    _sleep_cache[breath] = img
    return img


def _ball(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float) -> None:
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BALL)
    draw.ellipse([cx - r * 0.55, cy - r * 0.6, cx - r * 0.05, cy - r * 0.1], fill=BALL_HI)


def _font(px: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype(kenji_font_path(), px)
    except OSError:
        return ImageFont.load_default()


def kenji_font_path() -> str:
    from . import widget
    return widget._fpath("Inter-Variable.ttf")


def mode_for(status: Status, working: bool, idle_for: float) -> str:
    if working:
        return "work"
    if status.color == RED:
        return "bow"
    return "sleep" if idle_for >= SLEEP_AFTER else "ball"


def render(status: Status, working: bool, idle_for: float, t: float) -> tuple[Image.Image, str]:
    mode = mode_for(status, working, idle_for)
    img = Image.new("RGBA", (W, H), PANEL)
    d = ImageDraw.Draw(img)
    d.line([(10, GROUND), (W - 10, GROUND)], fill=LINE, width=2)
    tick = int(t * 4)                      # 4 sprite frames per second

    dog_y = 0
    ball = None
    if mode == "work":
        frame = kenji._compose(*kenji._frame_layers("sit", tick)[0])
        px = frame.load()
        screen = kenji._data()["points"]["screenCells"]
        for i, (x, y) in enumerate(screen):
            px[x, y] = kenji._hex(kenji._data()["palette"]["B" if (i + tick) % 3 else "Y"])
    elif mode == "sleep":
        frame = _sleep_frame(int(t * 0.8) % 2)
    else:
        # ball bounces back and forth in front of the dog; Bigotes bows when it comes close and hops with it
        u = t * 0.22
        tri = abs(((u % 2) - 1))               # 0..1..0 triangle wave
        bx = 185 + tri * 90
        near = bx < 215
        hop = abs(math.sin(t * 2.6 * math.pi / 2))
        by = GROUND - 8 - hop * 46
        ball = (bx, by)
        pose = "bow" if (mode == "bow" or near) else "stand"
        layers, eyes = kenji._frame_layers(pose, tick)
        frame = kenji._compose(*layers)
        if near:
            dog_y = -int(abs(math.sin(t * 5)) * 4)
        if mode == "bow":
            ball = None
        if pose == "stand" and tick % 8 == 7:
            p = frame.load()
            for x, y in eyes:
                p[x, y] = kenji._blink_color()

    big = frame.resize((frame.width * SCALE, frame.height * SCALE), Image.NEAREST)
    img.alpha_composite(big, (DOG_X, GROUND - big.height + 3 + dog_y))

    if ball:
        sh = max(3, 9 - (GROUND - ball[1]) / 8)
        d.ellipse([ball[0] - sh, GROUND - 3, ball[0] + sh, GROUND + 1], fill=LINE)
        _ball(d, ball[0], ball[1], 8)

    if mode == "sleep":
        for i in range(3):
            ph = (t * 0.5 + i / 3) % 1.0
            zx = DOG_X + 150 + ph * 24 + i * 6
            zy = GROUND - 62 - ph * 30
            a = int(255 * (1 - ph))
            d.text((zx, zy), "z" if i % 2 else "Z", font=_font(int(11 + 6 * ph)), fill=ZZ[:3] + (a,))

    # rounded corners
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], 14, fill=255)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out, mode
