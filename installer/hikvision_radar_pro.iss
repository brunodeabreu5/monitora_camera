#define MyAppName "Hikvision Radar Pro"
#ifndef MyAppVersion
  #define MyAppVersion "4.2.0"
#endif
#ifndef MyAppExeName
  #define MyAppExeName "HikvisionRadarProV42.exe"
#endif
#ifndef MyAppPublisher
  #define MyAppPublisher "Hikvision Radar Pro"
#endif
#ifndef MyAppSourceDir
  #define MyAppSourceDir "..\\dist"
#endif
#ifndef MyOutputDir
  #define MyOutputDir "..\\release"
#endif

[Setup]
AppId={{A8DB92C8-8AC2-4D40-9A07-4798DB05E1E0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\HikvisionRadarPro
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
OutputDir={#MyOutputDir}
OutputBaseFilename=HikvisionRadarPro-{#MyAppVersion}-setup
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos adicionais:"

[Files]
Source: "{#MyAppSourceDir}\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Executar {#MyAppName}"; Flags: nowait postinstall skipifsilent
