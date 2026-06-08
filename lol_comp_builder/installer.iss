[Setup]
AppId={{F5A706FA-33D6-468D-9058-9BF06F5B80C2}
AppName=CompMaker
AppVersion=1.0.0
AppPublisher=CompMaker
DefaultDirName={autopf}\CompMaker
DefaultGroupName=CompMaker
AllowNoIcons=yes
DisableProgramGroupPage=yes
OutputDir=..\Installer
OutputBaseFilename=CompMaker-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
UninstallDisplayIcon={app}\CompMaker.exe
SetupIconFile=assets\icon.ico
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Dirs]
Name: "{localappdata}\CompMaker"
Name: "{localappdata}\CompMaker\data"
Name: "{localappdata}\CompMaker\assets"
Name: "{localappdata}\CompMaker\retratos"

[Files]
Source: "dist_release\CompMaker.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\CompMaker"; Filename: "{app}\CompMaker.exe"
Name: "{group}\Desinstalar CompMaker"; Filename: "{uninstallexe}"
Name: "{autodesktop}\CompMaker"; Filename: "{app}\CompMaker.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\CompMaker.exe"; Description: "Iniciar CompMaker"; Flags: nowait postinstall skipifsilent
