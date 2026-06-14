[Setup]
AppId={{F5A706FA-33D6-468D-9058-9BF06F5B80C2}
AppName=CompMaker
AppVersion=1.1.8
AppVerName=CompMaker 1.1.8
AppPublisher=CompMaker
DefaultDirName={localappdata}\Programs\CompMaker
DefaultGroupName=CompMaker
AllowNoIcons=yes
DisableProgramGroupPage=yes
OutputDir=..\Installer
OutputBaseFilename=CompMaker-Setup-1.1.8
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UsePreviousAppDir=yes
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\CompMaker.exe
SetupIconFile=assets\icon.ico
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion=1.1.8.0
VersionInfoProductName=CompMaker
VersionInfoProductVersion=1.1.8
VersionInfoDescription=CompMaker Installer

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

[Code]
function IsOllamaInstalled(): Boolean;
begin
  Result :=
    FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe')) or
    FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama app.exe')) or
    FileExists(ExpandConstant('{commonpf}\Ollama\ollama.exe')) or
    FileExists(ExpandConstant('{commonpf}\Ollama\ollama app.exe'));
end;

function GetWingetPath(): string;
var
  Candidate: string;
begin
  Candidate := ExpandConstant('{localappdata}\Microsoft\WindowsApps\winget.exe');
  if FileExists(Candidate) then
  begin
    Result := Candidate;
    exit;
  end;

  Candidate := ExpandConstant('{sys}\winget.exe');
  if FileExists(Candidate) then
  begin
    Result := Candidate;
    exit;
  end;

  Result := '';
end;

procedure InstallOllamaIfMissing();
var
  WingetPath: string;
  ResultCode: Integer;
begin
  if IsOllamaInstalled() then
    exit;

  WingetPath := GetWingetPath();
  if WingetPath = '' then
  begin
    SuppressibleMsgBox(
      'CompMaker necesita Ollama para descargar y usar modelos locales, pero Windows no tiene winget disponible.' + #13#10 + #13#10 +
      'Instala Ollama manualmente después de terminar la instalación.',
      mbInformation,
      MB_OK,
      IDOK
    );
    exit;
  end;

  WizardForm.StatusLabel.Caption := 'Instalando Ollama automáticamente...';
  WizardForm.Update();

  if not Exec(
    WingetPath,
    'install --id Ollama.Ollama --exact --accept-package-agreements --accept-source-agreements --disable-interactivity',
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  ) then
  begin
    SuppressibleMsgBox(
      'No se pudo iniciar la instalación automática de Ollama.' + #13#10 + #13#10 +
      'Puedes instalarlo manualmente después de terminar la instalación.',
      mbInformation,
      MB_OK,
      IDOK
    );
    exit;
  end;

  if (ResultCode <> 0) and not IsOllamaInstalled() then
  begin
    SuppressibleMsgBox(
      'La instalación automática de Ollama no terminó correctamente (código ' + IntToStr(ResultCode) + ').' + #13#10 + #13#10 +
      'CompMaker se ha instalado igualmente, pero tendrás que instalar Ollama manualmente para usar modelos locales.',
      mbInformation,
      MB_OK,
      IDOK
    );
    exit;
  end;

  WizardForm.StatusLabel.Caption := 'Ollama instalado correctamente.';
  WizardForm.Update();
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    InstallOllamaIfMissing();
end;
