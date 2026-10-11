"""Enable/disable 'Start with Windows' via the registry Run key (HKCU)."""
from __future__ import annotations

import sys
from pathlib import Path

_APP_NAME = "ClaudeUsageTray"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _command() -> str:
    """Command Windows will run at boot."""
    if getattr(sys, "frozen", False):  # already built as an .exe
        return f'"{sys.executable}"'
    # dev mode: run as a module with pythonw (no console window)
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = pyw if pyw.exists() else Path(sys.executable)
    return f'"{exe}" -m claude_usage_tray'


def is_enabled() -> bool:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            winreg.QueryValueEx(k, _APP_NAME)
        return True
    except (FileNotFoundError, OSError, ImportError):
        return False


def enable() -> None:
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
        winreg.SetValueEx(k, _APP_NAME, 0, winreg.REG_SZ, _command())


def disable() -> None:
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, _APP_NAME)
    except (FileNotFoundError, OSError, ImportError):
        pass


def toggle() -> bool:
    """Toggle the state and return the new state (True=enabled)."""
    if is_enabled():
        disable()
        return False
    enable()
    return True
