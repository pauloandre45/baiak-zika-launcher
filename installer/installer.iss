; Baiak-Zika Installer Script
; Inno Setup Script

#define MyAppName "Baiak-Zika"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Baiak-Zika Server"
#define MyAppURL "https://github.com/pauloandre45/baiak-zika-launcher"
#define MyAppExeName "Baiak-Zika.exe"

[Setup]
; Identificador único do app
AppId={{B4A1AK-Z1KA-2024-LAUNCHER-GAME}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Pasta de instalação padrão (AppData\Local)
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}

; Não permite mudar pasta (instala sempre no AppData)
DisableDirPage=yes

; Saída do instalador
OutputDir=output
OutputBaseFilename=Baiak-Zika-Instalador
SetupIconFile=icon.ico

; Compressão
Compression=lzma2/ultra64
SolidCompression=yes

; Privilégios (não precisa admin)
PrivilegesRequired=lowest

; Visual
WizardStyle=modern
WizardSizePercent=100

; Desinstalar
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"; Flags: checked

[Files]
; Launcher executável
Source: "files\Baiak-Zika.exe"; DestDir: "{app}"; Flags: ignoreversion

; Arquivos de configuração
Source: "files\local_config.json"; DestDir: "{app}"; Flags: ignoreversion

; Ícone (se existir)
Source: "files\icon.ico"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; Atalho na Área de Trabalho
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; Atalho no Menu Iniciar
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
; Executar launcher após instalação
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
// Mensagem personalizada após instalação
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Instalação concluída
  end;
end;
