"""Main module — runs the tray loop, polls usage, changes the icon colour, notifies, and blinks when red."""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import threading
from typing import Any

import pystray

from . import autostart, config, icon as icon_mod, ui
from .api import fetch_usage, read_access_token
from .status import RED, Status, evaluate, humanize_reset


class TrayApp:
    def __init__(self) -> None:
        self.cfg: dict[str, Any] = config.load()
        self.status: Status = Status("unknown", None, None, [], error="Loading…")
        self._last_color: str | None = None
        self._stop = threading.Event()
        self._wake = threading.Event()   # wake up to poll immediately (Refresh)
        self._blink_on = False

        self.icon = pystray.Icon(
            "claude_usage_tray",
            icon=icon_mod.render(self.status, self.cfg),
            title="Claude Usage — Loading…",
            menu=self._build_menu(),
        )

    # ---------- menu ----------
    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(lambda _: self._headline(), None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Refresh now", self._on_refresh),
            pystray.MenuItem("Show details…", self._on_details, default=True),
            pystray.MenuItem("Floating widget", self._on_widget),
            pystray.MenuItem("Connect Claude account…", self._on_connect),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Start with Windows",
                self._on_toggle_autostart,
                checked=lambda _: autostart.is_enabled(),
            ),
            pystray.MenuItem(
                "Notifications (balloon)",
                self._on_toggle_notify,
                checked=lambda _: self.cfg.get("notify", True),
            ),
            pystray.MenuItem(
                "Popup alert below 50%/20%",
                self._on_toggle_popup,
                checked=lambda _: self.cfg.get("popup_alert", True),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("About", self._on_about),
            pystray.MenuItem("Quit", self._on_quit),
        )

    def _headline(self) -> str:
        s = self.status
        if s.error:
            return f"⚠ {s.error}"
        if s.remaining_pct is None:
            return "No data"
        dot = {"green": "🟢", "orange": "🟠", "red": "🔴"}.get(s.color, "⚪")
        return f"{dot} {s.remaining_pct:.0f}% left"

    def _details_text(self) -> str:
        s = self.status
        if s.error:
            return f"Status: {s.error}"
        lines = ["Remaining quota (Claude Code)\n"]
        for q in s.quotas:
            mark = "  ← sets colour" if q.key == s.driver else ""
            lines.append(
                f"• {q.label}: {q.remaining_pct:.0f}% left  "
                f"(used {q.used_pct:.0f}%, resets {humanize_reset(q.resets_at)}){mark}"
            )
        lines.append("\nColour thresholds: green >50%  |  orange ≤50%  |  red ≤20%")
        lines.append(f"Updates every {self.cfg['poll_seconds']} seconds")
        return "\n".join(lines)

    # ---------- callbacks ----------
    def _on_refresh(self, *_):
        self._wake.set()

    def _on_details(self, *_):
        try:
            ui.show_details(lambda: self.status, self.cfg, self._on_refresh)
        except Exception:  # noqa: BLE001 — fall back to a MessageBox if tkinter has problems
            threading.Thread(
                target=lambda: ctypes.windll.user32.MessageBoxW(0, self._details_text(), "Claude Usage", 0x40),
                daemon=True,
            ).start()

    def _on_connect(self, *_):
        ui.show_onboarding(self._recheck_token, self._open_login, self._has_cli)

    def _on_about(self, *_):
        ui.show_about(lambda: self.status, self.cfg)

    def _on_widget(self, *_):
        ui.show_widget(lambda: self.status, self.cfg, self._on_refresh)

    @staticmethod
    def _has_cli() -> bool:
        return shutil.which("claude") is not None

    def _recheck_token(self) -> bool:
        if read_access_token():
            self._wake.set()  # token found -> poll immediately
            return True
        return False

    @staticmethod
    def _open_login() -> None:
        """Open a terminal so the user can log in through the official Claude Code."""
        try:
            if os.name == "nt":
                subprocess.Popen(
                    'start "Claude Login" cmd /k claude',
                    shell=True,
                )
            else:
                subprocess.Popen(["claude"])
        except Exception:  # noqa: BLE001
            pass

    def _on_toggle_autostart(self, *_):
        autostart.toggle()

    def _on_toggle_notify(self, *_):
        self.cfg["notify"] = not self.cfg.get("notify", True)
        config.save(self.cfg)

    def _on_toggle_popup(self, *_):
        self.cfg["popup_alert"] = not self.cfg.get("popup_alert", True)
        config.save(self.cfg)

    def _on_quit(self, *_):
        self._stop.set()
        self._wake.set()
        self.icon.stop()

    # ---------- work loop ----------
    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            self._refresh_once()
            # wait until the next cycle, or until woken (Refresh/Quit)
            self._wake.wait(timeout=self.cfg["poll_seconds"])
            self._wake.clear()

    def _refresh_once(self) -> None:
        new = evaluate(fetch_usage(), self.cfg)
        prev = self.status
        self.status = new
        self._apply_icon()
        self._maybe_notify(prev, new)

    def _apply_icon(self) -> None:
        self.icon.icon = icon_mod.render(self.status, self.cfg)
        self.icon.title = self._tooltip()
        self._last_color = self.status.color

    def _tooltip(self) -> str:
        s = self.status
        if s.error:
            return f"Claude Usage — {s.error}"
        if s.remaining_pct is None:
            return "Claude Usage"
        parts = [f"{q.label}: {q.remaining_pct:.0f}%" for q in s.quotas[:3]]
        return "Claude Usage — left: " + "  |  ".join(parts)

    def _maybe_notify(self, prev: Status, new: Status) -> None:
        order = {"unknown": 0, "green": 0, "orange": 1, "red": 2}
        # notify only when things get "worse" across a level (green->orange, orange->red)
        if not (order.get(new.color, 0) > order.get(prev.color, 0) and new.remaining_pct is not None):
            return

        is_red = new.color == RED
        label = "Quota almost used up!" if is_red else "Quota is getting low"
        reset = humanize_reset(_driver_reset(new))

        # 1) notification balloon
        if self.cfg.get("notify", True):
            try:
                self.icon.notify(f"{label} {new.remaining_pct:.0f}% left\nResets {reset}", "Claude Usage")
            except Exception:  # noqa: BLE001
                pass

        # 2) graphical alert popup (stays on screen) when crossing below 50%/20%
        if self.cfg.get("popup_alert", True):
            try:
                ui.show_alert(new, self.cfg, is_red, reset)
            except Exception:  # noqa: BLE001 — fallback MessageBox
                flags = (0x10 if is_red else 0x30) | 0x40000
                threading.Thread(
                    target=lambda: ctypes.windll.user32.MessageBoxW(
                        0, f"{label} {new.remaining_pct:.0f}% left", "Claude Usage", flags),
                    daemon=True,
                ).start()

    def _blink_loop(self) -> None:
        while not self._stop.is_set():
            if icon_mod.should_blink(self.status, self.cfg):
                self._blink_on = not self._blink_on
                try:
                    self.icon.icon = icon_mod.render(self.status, self.cfg, dim=self._blink_on)
                except Exception:  # noqa: BLE001
                    pass
                self._stop.wait(0.6)
            else:
                if self._blink_on:  # just stopped blinking -> restore the full icon
                    self._blink_on = False
                    self._apply_icon()
                self._stop.wait(0.5)

    def run(self) -> None:
        # first run and not logged in -> open the onboarding window to help connect the account
        if not read_access_token():
            ui.show_onboarding(self._recheck_token, self._open_login, self._has_cli)
        elif self.cfg.get("widget_on_start"):
            ui.show_widget(lambda: self.status, self.cfg, self._on_refresh)
        threading.Thread(target=self._poll_loop, daemon=True).start()
        threading.Thread(target=self._blink_loop, daemon=True).start()
        self.icon.run()


def _driver_reset(s: Status) -> str | None:
    for q in s.quotas:
        if q.key == s.driver:
            return q.resets_at
    return None


def main() -> None:
    TrayApp().run()
