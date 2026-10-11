"""Convert the usage response -> colour status + summary numbers for the tooltip/popup."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

# Status levels, ordered good -> bad
GREEN = "green"
ORANGE = "orange"
RED = "red"
UNKNOWN = "unknown"

# RGB colours for drawing the icon
COLORS = {
    GREEN: (34, 197, 94),    # #22C55E
    ORANGE: (245, 158, 11),  # #F59E0B
    RED: (239, 68, 68),      # #EF4444
    UNKNOWN: (148, 163, 184),  # grey #94A3B8
}

# Label for each quota
LABELS = {
    "five_hour": "5 hours",
    "seven_day": "Weekly",
    "seven_day_opus": "Opus (weekly)",
    "seven_day_sonnet": "Sonnet (weekly)",
}


@dataclass
class Quota:
    key: str
    label: str
    used_pct: float       # % used (utilization)
    remaining_pct: float  # % remaining
    resets_at: str | None


@dataclass
class Status:
    color: str                 # GREEN/ORANGE/RED/UNKNOWN
    remaining_pct: float | None  # remaining of the worst quota
    driver: str | None         # key of the quota that determines the colour
    quotas: list[Quota]        # every quota that could be read (shown in the popup)
    error: str | None = None


def _classify(remaining: float, cfg: dict[str, Any]) -> str:
    if remaining <= cfg["red_at"]:
        return RED
    if remaining <= cfg["orange_at"]:
        return ORANGE
    return GREEN


def evaluate(usage: dict[str, Any], cfg: dict[str, Any]) -> Status:
    """Compute the status from the fetch_usage() response."""
    if usage.get("error"):
        return Status(UNKNOWN, None, None, [], error=usage.get("message") or usage["error"])

    quotas: list[Quota] = []
    for key, val in usage.items():
        if not isinstance(val, dict):
            continue
        util = val.get("utilization")
        if util is None:
            continue  # quota not started yet (e.g. seven_day_opus = null)
        used = float(util)
        quotas.append(
            Quota(
                key=key,
                label=LABELS.get(key, key),
                used_pct=used,
                remaining_pct=max(0.0, 100.0 - used),
                resets_at=val.get("resets_at"),
            )
        )

    if not quotas:
        return Status(UNKNOWN, None, None, [], error="No quota data")

    # pick the colour from the quota the user told us to watch (watch) with the least remaining = worst
    watched = [q for q in quotas if q.key in cfg["watch"]] or quotas
    worst = min(watched, key=lambda q: q.remaining_pct)
    color = _classify(worst.remaining_pct, cfg)

    quotas.sort(key=lambda q: q.remaining_pct)  # worst first in the popup
    return Status(color, worst.remaining_pct, worst.key, quotas)


def humanize_reset(resets_at: str | None) -> str:
    """Convert an ISO timestamp -> 'in 2h 14m' (approximate)."""
    if not resets_at:
        return "-"
    try:
        dt = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
    except ValueError:
        return "-"
    delta = dt - datetime.now(timezone.utc)
    secs = int(delta.total_seconds())
    if secs <= 0:
        return "soon"
    h, rem = divmod(secs, 3600)
    m = rem // 60
    if h >= 24:
        d, hh = divmod(h, 24)
        return f"in {d}d {hh}h"
    if h:
        return f"in {h}h {m}m"
    return f"in {m}m"
