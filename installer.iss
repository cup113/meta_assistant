; Inno Setup script for Meta Assistant
#define MyAppName "Meta Assistant"
#define MyAppExeName "meta_assistant.exe"

[Setup]
AppId={{3AF86D76-ACB4-4C8C-892F-1AC8D1CB7808}}
AppName={#MyAppName}
AppVersion={#APP_VERSION}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=dist
OutputBaseFilename=meta-assistant-{#APP_VERSION}-setup
SetupIconFile=assistant.ico
UninstallDisplayIcon={app}\assistant.ico
Compression=lzma
SolidCompression=yes

[Tasks]
Name: desktopicon; Description: "Create desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "dist\meta_assistant.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
Source: "assistant.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
