@echo off
REM Build the .exe and wrap it in an installer wizard in one command
cd /d "%~dp0"
where py >nul 2>nul && (set PY=py) || (set PY=python)

echo [1/3] Installing dependencies...
%PY% -m pip install -q -r requirements.txt pyinstaller || goto :err

echo [2/3] Building the .exe with PyInstaller...
%PY% build.py || goto :err

echo [3/3] Building the installer with Inno Setup...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
  echo   ** Inno Setup not found — only dist\ClaudeUsageTray.exe was produced
  echo   ** Download: https://jrsoftware.org/isdl.php and run build_all.bat again
  goto :done
)
%ISCC% installer.iss || goto :err
echo.
echo Done! The installer is at: dist_installer\ClaudeUsageTray-Setup.exe

:done
echo.
echo Files ready to distribute:
echo   - Portable : dist\ClaudeUsageTray.exe
echo   - Installer: dist_installer\ClaudeUsageTray-Setup.exe
pause
exit /b 0

:err
echo.
echo An error occurred; see the log above
pause
exit /b 1
