"""Draw the system-tray icon — the Claude star/spark coloured by status + a gauge ring.

Star colour = main signal (green/orange/red). Outer ring = the share "already used".
The remaining-% number (optional) goes in the lower-right corner.
"""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from . import kenji
from .status import COLORS, RED, Status

_SIZE = 256          # draw large and let pystray shrink it = sharper
_N_RAYS = 11         # number of rays in the Claude spark
_BG = (0, 0, 0, 0)   # transparent


def _petal(color: tuple[int, int, int], inner: float, outer: float, width: float) -> Image.Image:
    """Create a single ray image (vertical, pointing up) with rounded ends, to be rotated around the centre."""
    layer = Image.new("RGBA", (_SIZE, _SIZE), _BG)
    d = ImageDraw.Draw(layer)
    cx = _SIZE / 2
    top = cx - outer
    bottom = cx - inner
    half = width / 2
    # vertical capsule = rectangle + a circle at each end (rounded ends)
    d.rounded_rectangle(
        [cx - half, top, cx + half, bottom],
        radius=half,
        fill=color + (255,),
    )
    return layer


def _starburst(color: tuple[int, int, int], alpha: int = 255) -> Image.Image:
    """Assemble all the rays into a Claude-logo-style spark (full frame)."""
    burst = Image.new("RGBA", (_SIZE, _SIZE), _BG)
    # rays reach almost to the edge + wider = a large graphic filling the icon
    petal = _petal(color, inner=_SIZE * 0.05, outer=_SIZE * 0.485, width=_SIZE * 0.135)
    for i in range(_N_RAYS):
        angle = i * (360 / _N_RAYS)
        burst.alpha_composite(petal.rotate(angle, resample=Image.BICUBIC, center=(_SIZE / 2, _SIZE / 2)))
    if alpha < 255:
        band = burst.split()[3].point(lambda a: int(a * alpha / 255))
        burst.putalpha(band)
    return burst


def _ring(draw: ImageDraw.ImageDraw, used_pct: float, color: tuple[int, int, int]) -> None:
    """Outer gauge ring: full circle = 100% used."""
    pad = _SIZE * 0.03
    box = [pad, pad, _SIZE - pad, _SIZE - pad]
    w = int(_SIZE * 0.07)
    # faint track
    draw.arc(box, 0, 360, fill=color + (55,), width=w)
    # the used part, starting from the top (-90°), clockwise
    sweep = max(0.0, min(100.0, used_pct)) / 100 * 360
    if sweep > 0:
        draw.arc(box, -90, -90 + sweep, fill=color + (255,), width=w)


def _best_font(px: int):
    for name in ("segoeuib.ttf", "arialbd.ttf", "segoeui.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_center_number(img: Image.Image, remaining: float, color: tuple[int, int, int]) -> None:
    """Remaining-% number drawn large in the centre of the icon on a solid disc, easy to read even when the icon is small."""
    d = ImageDraw.Draw(img)
    txt = f"{int(round(remaining))}"

    # solid round backing disc in the centre so the number stands out over the spark
    r = int(_SIZE * 0.375)
    cx = cy = _SIZE // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(15, 23, 42, 245))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color + (255,), width=int(_SIZE * 0.03))

    # pick the largest font size that still fits in the disc (1-3 digits)
    max_w = int(r * 1.55)
    px = int(_SIZE * (0.62 if len(txt) == 1 else 0.50 if len(txt) == 2 else 0.38))
    while px > 8:
        font = _best_font(px)
        bb = d.textbbox((0, 0), txt, font=font)
        if bb[2] - bb[0] <= max_w:
            break
        px -= 6
    bb = d.textbbox((0, 0), txt, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((cx - tw / 2 - bb[0], cy - th / 2 - bb[1]), txt, font=font, fill=color + (255,))


def render(status: Status, cfg: dict, dim: bool = False, tick: int = 0, working: bool = False) -> Image.Image:
    """Build the icon image from the status. dim=True is used when blinking (faded frame)."""
    if cfg.get("icon_style", "kenji") == "kenji":
        try:
            return kenji.render(status, tick, working, dim)
        except Exception:  # noqa: BLE001 — sprite missing/corrupt -> classic icon
            pass
    color = COLORS[status.color]
    img = Image.new("RGBA", (_SIZE, _SIZE), _BG)
    d = ImageDraw.Draw(img)

    used = 100.0 - (status.remaining_pct if status.remaining_pct is not None else 100.0)
    show_num = cfg.get("show_percent_text") and status.remaining_pct is not None
    _ring(d, used, color)
    # if the number is shown, fade the spark into the background so the number stands out
    img.alpha_composite(_starburst(color, alpha=150 if show_num else 255))

    if show_num:
        _draw_center_number(img, status.remaining_pct, color)

    if dim:
        # faded frame for blinking (lower alpha over the whole image)
        alpha = img.split()[3].point(lambda a: int(a * 0.35))
        img.putalpha(alpha)

    return img


def should_blink(status: Status, cfg: dict) -> bool:
    if cfg.get("icon_style", "kenji") == "kenji":
        return False  # Kenji bows instead of blinking
    return bool(cfg.get("blink_when_red")) and status.color == RED
