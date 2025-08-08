#define MyAppName "Autoparser"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Autoparser Team"
#define MyAppExeName "Autoparser.exe"

[Setup]
AppId={{A3E8C5C2-5B55-4D8B-9B8B-0F1E5A40C8DD}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputBaseFilename={#MyAppName}-Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "{#SourcePath}\dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
