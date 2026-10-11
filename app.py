"""Entry point for PyInstaller (absolute imports).

In dev mode `python -m claude_usage_tray` works as before; this file exists so the build
can point at it without relative-import problems when run as a top-level script.
"""
from claude_usage_tray.tray import main

if __name__ == "__main__":
    main()
