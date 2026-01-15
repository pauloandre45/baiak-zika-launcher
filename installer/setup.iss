; Baiak-Zika Launcher Installer
; Criado com Inno Setup

#define MyAppName "Baiak-Zika"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Baiak-Zika"
#define MyAppURL "https://www.baiak-zika.com"
#define MyAppExeName "Baiak-Zika.exe"

[Setup]
; Identificador único do app (GUID)
AppId={{B4A14K-Z1K4-L4UNCH3R-2026}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Instalar em AppData\Local\Baiak-Zika
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}

; Não precisa de privilégios de admin
PrivilegesRequired=lowest

; Configurações do instalador
AllowNoIcons=yes
OutputDir=Output
OutputBaseFilename=Baiak-Zika-Setup
SetupIconFile=..\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Visual
WizardImageFile=wizard_image.bmp
WizardSmallImageFile=wizard_small.bmp

; Desinstalador
UninstallDisplayIcon={app}\icon.ico
UninstallDisplayName={#MyAppName} Launcher

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"; Flags: checked

[Files]
; Executável principal
Source: "..\dist\Baiak-Zika.exe"; DestDir: "{app}"; Flags: ignoreversion

; Ícone
Source: "..\icon.ico"; DestDir: "{app}"; Flags: ignoreversion

; Pasta assets
Source: "..\dist\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Atalho na Área de Trabalho com ícone do Tibia
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

; Atalho no Menu Iniciar
Name: "{userprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{userprograms}\{#MyAppName}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"

[Run]
; Opção para executar após instalação
Filename: "{app}\{#MyAppExeName}"; Description: "Executar {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
// Função para verificar se já existe instalação anterior
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

// Limpar pasta do cliente ao desinstalar (opcional - perguntar ao usuário)
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ClientPath: String;
  MsgResult: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    ClientPath := ExpandConstant('{app}\Baiak-zika-15');
    if DirExists(ClientPath) then
    begin
      MsgResult := MsgBox('Deseja remover também os arquivos do cliente do jogo?' + #13#10 + 
                          '(Isso vai apagar suas configurações e dados salvos)', 
                          mbConfirmation, MB_YESNO);
      if MsgResult = IDYES then
      begin
        DelTree(ClientPath, True, True, True);
      end;
    end;
  end;
end;
