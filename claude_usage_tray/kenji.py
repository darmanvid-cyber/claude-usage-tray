"""Kenji — animated pixel-art golden retriever used as the tray icon.

Poses: standing + tail wag (idle), sitting at a laptop with glasses (Claude Code working),
play-bow (quota red). A bar under the dog shows the remaining quota in the status colour.
Drawing only: nothing here touches the API, the poll interval or the alert logic.
"""
from __future__ import annotations

import json
import sys
import time
from functools import lru_cache
from pathlib import Path

from PIL import Image

from . import config
from .status import COLORS, RED, Status

_SIZE = 256
_WORK_WINDOW = 20.0      # seconds since the last write to a session .jsonl = "working"
_SCAN_EVERY = 3.0
_PROJECTS = Path.home() / ".claude" / "projects"

_scan_cache = (0.0, False)


def _sprite_path() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" / "kenji-sprite.json"


# Coat colour overrides on top of the sprite palette (G=main fur, D=shade/ears, L=light, M=mid)
COATS: dict[str, dict[str, list[int]]] = {
    "golden": {},
    "beagle": {"G": [238, 206, 120], "D": [190, 140, 64], "L": [255, 248, 232], "M": [248, 232, 190]},
}


@lru_cache(maxsize=1)
def _data() -> dict:
    d = json.loads(_sprite_path().read_text(encoding="utf-8"))
    d["palette"].update(COATS.get(config.load().get("kenji_coat", "beagle"), {}))
    return d


def _hex(c: list[int]) -> tuple[int, int, int, int]:
    return (c[0], c[1], c[2], 255)


@lru_cache(maxsize=None)
def _layer(name: str) -> Image.Image:
    d = _data()
    pal = {k: _hex(v) for k, v in d["palette"].items()}
    img = Image.new("RGBA", (d["columns"], d["rows"]), (0, 0, 0, 0))
    px = img.load()
    for y, row in enumerate(d["layers"][name]):
        for x, ch in enumerate(row):
            if ch != d["transparent"] and ch in pal:
                px[x, y] = pal[ch]
    return img


def _compose(*names: str) -> Image.Image:
    d = _data()
    img = Image.new("RGBA", (d["columns"], d["rows"]), (0, 0, 0, 0))
    for n in names:
        img.alpha_composite(_layer(n))
    return img


_POSE_COMBOS = {
    "stand": (("standTail0",), ("standTail12",)),
    "bow": (("bowTailUp",), ("bowTailOut",)),
    "sit": (("sitTail30", "sitPawDown", "laptop", "glasses"),
            ("sitTail70", "sitPawUp", "laptop", "glasses")),
}


@lru_cache(maxsize=None)
def _crop_box(pose: str) -> tuple[int, int, int, int]:
    """Union bounding box of one pose's frames: the dog fills the icon without jumping while animating."""
    boxes = [b for combo in _POSE_COMBOS[pose] if (b := _compose(*combo).getbbox())]
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def is_working() -> bool:
    """True if a Claude Code session wrote to a transcript recently (cached for a few seconds)."""
    global _scan_cache
    now = time.time()
    if now - _scan_cache[0] < _SCAN_EVERY:
        return _scan_cache[1]
    working = False
    try:
        for proj in _PROJECTS.iterdir():
            if not proj.is_dir():
                continue
            for f in proj.glob("*.jsonl"):
                if now - f.stat().st_mtime < _WORK_WINDOW:
                    working = True
                    break
            if working:
                break
    except OSError:
        pass
    _scan_cache = (now, working)
    return working


def pose_for(status: Status, working: bool) -> str:
    if status.color == RED:
        return "bow"
    return "sit" if working else "stand"


def _frame_layers(pose: str, tick: int) -> tuple[list[str], list[list[int]]]:
    pts = _data()["points"]
    if pose == "bow":
        return [("bowTailUp", "bowTailOut")[tick % 2]], pts["bowEyes"]
    if pose == "sit":
        tail = ("sitTail30", "sitTail50", "sitTail70", "sitTail50")[tick % 4]
        paw = ("sitPawDown", "sitPawUp")[tick % 2]
        return [tail, "laptop", paw, "glasses"], pts["sitEyes"]
    return [("standTail0", "standTail12")[tick % 2]], pts["standEyes"]


def _blink_color() -> tuple[int, int, int, int]:
    return _hex(_data()["palette"]["G"])


def render(status: Status, tick: int, working: bool, dim: bool = False) -> Image.Image:
    pose = pose_for(status, working)
    names, eyes = _frame_layers(pose, tick)
    frame = _compose(*names)
    px = frame.load()
    if tick % 8 == 7 and pose != "sit":  # blink: paint over the eye pixels with fur colour
        for x, y in eyes:
            px[x, y] = _blink_color()
    if pose == "sit":                     # laptop screen flickers while "typing"
        screen = _data()["points"]["screenCells"]
        for i, (x, y) in enumerate(screen):
            px[x, y] = _hex(_data()["palette"]["B" if (i + tick) % 3 else "Y"])

    x0, y0, x1, y1 = _crop_box(pose)
    dog = frame.crop((x0, y0, x1, y1))
    w, h = dog.size
    bar_h, gap = 3, 2
    side = max(w, h + gap + bar_h)
    cell = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    top = (side - (h + gap + bar_h)) // 2
    cell.alpha_composite(dog, ((side - w) // 2, top))

    color = COLORS[status.color]
    by = top + h + gap
    bar_w = side - 2
    cpx = cell.load()
    for x in range(1, side - 1):
        for y in range(by, by + bar_h):
            cpx[x, y] = color + (70,)
    if status.remaining_pct is not None:
        fill = max(1, round(bar_w * max(0.0, min(100.0, status.remaining_pct)) / 100))
        for x in range(1, 1 + fill):
            for y in range(by, by + bar_h):
                cpx[x, y] = color + (255,)

    out = cell.resize((_SIZE, _SIZE), Image.NEAREST)  # fractional scale: fill the whole icon
    if dim:
        out.putalpha(out.split()[3].point(lambda a: int(a * 0.35)))
    return out
