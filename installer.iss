; Inno Setup script — builds the installer wizard for Claude Usage Tray
; Requires Inno Setup (https://jrsoftware.org/isdl.php); compile with:
;     "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
; Output: dist_installer\ClaudeUsageTray-Setup.exe

#define MyAppName "Claude Usage Tray"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "TopTier"
#define MyAppExeName "ClaudeUsageTray.exe"

[Setup]
AppId={{7B2C9E14-8A3F-4D2B-9C11-CLAUDEUSAGE01}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Claude Usage Tray
DefaultGroupName=Claude Usage Tray
DisableProgramGroupPage=yes
; Per-user install, no admin rights needed
PrivilegesRequired=lowest
OutputDir=dist_installer
OutputBaseFilename=ClaudeUsageTray-Setup
SetupIconFile=assets\app.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "thai"; MessagesFile: "compiler:Default.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Shortcuts:"
Name: "startup"; Description: "Start automatically when Windows starts (recommended)"; GroupDescription: "Startup:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\Claude Usage Tray"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall Claude Usage Tray"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Claude Usage Tray"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; autostart via the HKCU Run key (matches what the app manages itself) — created when the task is selected
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "ClaudeUsageTray"; ValueData: """{app}\{#MyAppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Claude Usage Tray now"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Close the program before uninstalling (avoids locked files)
Filename: "{cmd}"; Parameters: "/c taskkill /IM {#MyAppExeName} /F"; Flags: runhidden; RunOnceId: "KillApp"
