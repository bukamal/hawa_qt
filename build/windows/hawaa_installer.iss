; Inno Setup script for Hawaa.
; Build after PyInstaller created dist\Hawaa\Hawaa.exe.

#define MyAppName "Hawaa Al-Sham"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Hawaa"
#define MyAppExeName "Hawaa.exe"

[Setup]
AppId={{B4BC2A3C-81D6-4D94-96A1-4A0A5A1C0E10}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Hawaa Al-Sham
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\dist\installer
OutputBaseFilename=Hawaa_Setup
SetupIconFile=..\..\resources\branding\installer.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "إنشاء اختصار على سطح المكتب"; GroupDescription: "اختصارات إضافية:"; Flags: unchecked

[Files]
Source: "..\..\dist\Hawaa\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\resources\branding\app.ico"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\resources\branding\app.ico"

[Registry]
; Optional project file association for .hawa files.
Root: HKCR; Subkey: ".hawa"; ValueType: string; ValueName: ""; ValueData: "Hawaa.Project"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "Hawaa.Project"; ValueType: string; ValueName: ""; ValueData: "Hawaa Project File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "Hawaa.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\resources\branding\project_file.ico"
Root: HKCR; Subkey: "Hawaa.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "تشغيل {#MyAppName}"; Flags: nowait postinstall skipifsilent
