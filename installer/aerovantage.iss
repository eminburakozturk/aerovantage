; AeroVantage Inno Setup — logolu kurulum
; Derlemek icin: ISCC.exe installer\aerovantage.iss
; Once: python scripts\prepare_brand_icons.py && python scripts\build_exe.py

#define MyAppName "AeroVantage"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "AeroVantage"
#define MyAppURL "http://127.0.0.1:3000"
#define MyAppExeName "AeroVantage.exe"

[Setup]
AppId={{8F3C2A91-7B4E-4D1A-9C6E-AEROVANTAGE16}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\AeroVantage
DefaultGroupName=AeroVantage
DisableProgramGroupPage=yes
OutputDir=..\dist\setup
OutputBaseFilename=AeroVantage-Setup-{#MyAppVersion}
SetupIconFile=..\AeroVantage.ico
UninstallDisplayIcon={app}\AeroVantage.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "Masaüstü kısayolu oluştur"; GroupDescription: "Ek görevler:"; Flags: unchecked

[Files]
; Tray EXE (zorunlu)
Source: "..\AeroVantage.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\AeroVantage.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\AeroVantage.lnk"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\AeroVantage-Tray.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\AeroVantage-Setup.bat"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\install.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\launcher\app.py"; DestDir: "{app}\launcher"; Flags: ignoreversion
Source: "..\launcher\assets\*"; DestDir: "{app}\launcher\assets"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\scripts\*"; DestDir: "{app}\scripts"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "__pycache__\*,*.pyc"
; Brand assets (tray + frozen _MEIPASS fallback)
Source: "..\frontend\public\brand\*"; DestDir: "{app}\frontend\public\brand"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
Name: "{group}\AeroVantage"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\AeroVantage.ico"
Name: "{group}\AeroVantage Tray (bat)"; Filename: "{app}\AeroVantage-Tray.bat"; IconFilename: "{app}\AeroVantage.ico"
Name: "{group}\Kurulum (bağımlılıklar)"; Filename: "{app}\install.bat"; IconFilename: "{app}\AeroVantage.ico"
Name: "{autodesktop}\AeroVantage"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\AeroVantage.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\install.bat"; Parameters: "--quick"; Description: "Python/Node bağımlılıklarını kur"; Flags: postinstall skipifsilent shellexec
Filename: "{app}\{#MyAppExeName}"; Description: "AeroVantage'ı başlat"; Flags: nowait postinstall skipifsilent
