#define MyAppName "Kairos"
#define MyAppVersion "0.2.0"
#define MyAppExeName "Kairos.exe"

[Setup]
AppId={{A8AD9B44-5B3E-4C14-9D73-5CB314F5D530}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Kairos\app
DefaultGroupName=Kairos
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=Kairos-Setup
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\Kairos.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\Kairos"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar Kairos"; Flags: postinstall nowait skipifsilent
