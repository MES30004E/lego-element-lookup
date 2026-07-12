#define AppName "LEGO Element Lookup"
#ifndef AppVersion
  #define AppVersion "1.2.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\..\dist\LEGO Element Lookup"
#endif

[Setup]
AppId={{A252F0AE-799B-4930-81BE-7CE34EC725AE}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\LEGO Element Lookup
DefaultGroupName=LEGO Element Lookup
OutputDir=..\..\dist
OutputBaseFilename=LEGO-Element-Lookup-v{#AppVersion}-Windows-x86_64-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\LEGO Element Lookup.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\LEGO Element Lookup"; Filename: "{app}\LEGO Element Lookup.exe"
Name: "{autodesktop}\LEGO Element Lookup"; Filename: "{app}\LEGO Element Lookup.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\LEGO Element Lookup.exe"; Description: "Launch LEGO Element Lookup"; Flags: nowait postinstall skipifsilent
