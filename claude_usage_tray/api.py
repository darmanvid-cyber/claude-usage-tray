"""API client — reads Claude Code's OAuth token and queries the usage endpoint.

This module is the "only place" that touches the credential. It talks only to api.anthropic.com and
uses the token only in the Authorization header (never written to disk, never sent elsewhere).

Claude Code rotates (refreshes) the token itself in .credentials.json, so we just
re-read the file every cycle and never refresh it ourselves.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

import requests

API_URL_USAGE = "https://api.anthropic.com/api/oauth/usage"

CLAUDE_CONFIG_DIR = (
    Path(os.environ["CLAUDE_CONFIG_DIR"])
    if os.environ.get("CLAUDE_CONFIG_DIR")
    else Path.home() / ".claude"
)
CLAUDE_CREDENTIALS = CLAUDE_CONFIG_DIR / ".credentials.json"


def _credentials_path() -> Path:
    """Default credentials file; if missing, fall back to the config's `claude_config_dir`
    (e.g. a WSL path when Claude Code is logged in inside WSL)."""
    default = CLAUDE_CONFIG_DIR / ".credentials.json"
    if default.exists():
        return default
    from . import config
    alt = config.load().get("claude_config_dir")
    return Path(alt) / ".credentials.json" if alt else default

# If the claude CLI version cannot be found, use this instead (a User-Agent claude-code/* is required
# otherwise we land in a heavily rate-limited bucket and always get 429)
_FALLBACK_UA = "claude-code/2.1.204"
_cached_ua: str | None = None


def read_access_token() -> str | None:
    """Read the current accessToken from the credential file."""
    cred = _credentials_path()
    if not cred.exists():
        return None
    try:
        creds = json.loads(cred.read_text(encoding="utf-8"))
        return creds.get("claudeAiOauth", {}).get("accessToken") or None
    except (OSError, ValueError, KeyError):
        # OSError also covers a read colliding with Claude Code overwriting the file (token rotation)
        return None


def read_plan() -> str | None:
    """Read the plan name for the badge (e.g. 'Max (20×)' / 'Pro') from the credential."""
    cred = _credentials_path()
    if not cred.exists():
        return None
    try:
        o = json.loads(cred.read_text(encoding="utf-8")).get("claudeAiOauth", {})
    except (OSError, ValueError):
        return None
    sub = o.get("subscriptionType")
    tier = o.get("rateLimitTier") or ""
    name = sub.capitalize() if isinstance(sub, str) and sub else None
    m = re.search(r"(\d+)\s*x", str(tier), re.I)
    if name and m:
        return f"{name} ({m.group(1)}×)"
    return name


def _user_agent() -> str:
    global _cached_ua
    if _cached_ua:
        return _cached_ua
    ver = None
    try:
        out = subprocess.run(
            ["claude", "--version"],
            capture_output=True, text=True, timeout=5,
            shell=os.name == "nt",  # on Windows claude is a .cmd and must go through the shell
        )
        m = re.search(r"(\d+\.\d+\.\d+)", out.stdout or "")
        if m:
            ver = m.group(1)
    except Exception:
        pass
    _cached_ua = f"claude-code/{ver}" if ver else _FALLBACK_UA
    return _cached_ua


def _headers() -> dict[str, str] | None:
    token = read_access_token()
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": _user_agent(),
        "anthropic-beta": "oauth-2025-04-20",
    }


def fetch_usage() -> dict[str, Any]:
    """Fetch usage data. Always returns a dict; on error it has an 'error' key.

    Success format (key fields):
        {
          "five_hour": {"utilization": 33.0, "resets_at": "..."},
          "seven_day": {"utilization": 13.0, "resets_at": "..."},
          "seven_day_opus": null | {...},
          ...
        }
    utilization = % "already used" (0-100).
    """
    headers = _headers()
    if not headers:
        return {"error": "no_token", "message": "Token not found — log in to Claude Code first"}
    try:
        resp = requests.get(API_URL_USAGE, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.ConnectionError:
        return {"error": "connection", "message": "Could not connect"}
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else 0
        if code == 401:
            return {"error": "auth", "message": "Token expired — reopen Claude Code"}
        if code == 429:
            try:
                wait = int(e.response.headers.get("Retry-After", 0))
            except (TypeError, ValueError):
                wait = 0
            msg = f"Rate limited, retrying in {max(1, round(wait / 60))} min" if wait else "Rate limited (polling too often)"
            return {"error": "rate_limited", "message": msg, "retry_after": wait}
        return {"error": "http", "message": f"HTTP {code or '?'}"}
    except Exception as e:  # noqa: BLE001
        return {"error": "unknown", "message": str(e)[:80]}
