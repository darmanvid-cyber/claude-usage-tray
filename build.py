"""Build a single .exe with PyInstaller.

    pip install pyinstaller
    python build.py

Output is dist/ClaudeUsageTray.exe (runs as-is, no Python needed)
"""
import subprocess
import sys

import os

HERE = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.join(HERE, "assets", "app.ico")

ARGS = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--clean",
    "--onefile",
    "--windowed",              # no console window
    "--name", "ClaudeUsageTray",
    "--collect-submodules", "pystray",
    "--collect-submodules", "PIL",
]
if os.path.exists(ICON):
    ARGS += ["--icon", ICON]
FONTS = os.path.join(HERE, "assets", "fonts")
if os.path.isdir(FONTS):
    ARGS += ["--add-data", f"{FONTS}{os.pathsep}assets/fonts"]  # bundle the widget fonts
ARGS.append(os.path.join(HERE, "app.py"))

if __name__ == "__main__":
    raise SystemExit(subprocess.call(ARGS))
