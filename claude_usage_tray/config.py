"""User settings — load/save from a JSON file in the user's home.

Defaults are designed to be safe for the rate limit (poll every 180 s) and the colour thresholds
follow the user's choice: based on "tokens remaining" (remaining %).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_PATH = Path.home() / ".claude-usage-tray.json"

# Defaults — every value can be changed in the config file
DEFAULTS: dict[str, Any] = {
    # Seconds per poll. Don't go below 180 or you risk HTTP 429 from the API
    "poll_seconds": 180,
    # Colour thresholds, based on "percent remaining" (remaining = 100 - utilization)
    #   remaining > green_above           -> green
    #   orange_at >= remaining > red_at    -> orange
    #   remaining <= red_at                -> red (blinking)
    "green_above": 50,   # more than 50% left = green
    "orange_at": 50,     # 50% or less left = orange
    "red_at": 20,        # 20% or less left = red
    # Show a Windows notification (balloon) the first time a threshold is crossed downward
    "notify": True,
    # Show an alert popup (stays on screen) as soon as remaining drops below 50% and 20%
    "popup_alert": True,
    # Blink the red icon when nearly used up
    "blink_when_red": True,
    # Draw the remaining-% number over the icon (hard to read at 16px, clear at high DPI)
    "show_percent_text": True,
    # Which quotas count when choosing the colour (the worst one = least remaining)
    #   five_hour = 5-hour window, seven_day = weekly cap
    "watch": ["five_hour", "seven_day"],
    # tray icon: "kenji" (animated pixel-art dog) or "classic" (Claude spark + ring)
    "icon_style": "kenji",
    # floating widget (light theme)
    "widget_opacity": 0.94,     # opacity 0.5–1.0
    "widget_on_start": False,   # open the widget automatically at startup
}


def load() -> dict[str, Any]:
    """Load the config merged with defaults; write a sample file if none exists."""
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass  # corrupt file -> silently use the defaults
    else:
        save(cfg)
    return cfg


def save(cfg: dict[str, Any]) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
