#define AppName "LEGO Element Lookup"
; This fallback must match pyproject.toml. Release CI supplies /DAppVersion.
#ifndef AppVersion
  #define AppVersion "1.4.1"
#endif
#ifndef SourceDir
#define SourceDir "..\..\dist\LEGO Element Lookup"
#endif
#define AppPublisher "LEGO Element Lookup contributors"
#define AppURL "https://github.com/MES30004E/lego-element-lookup"
#define AppSupportURL "https://github.com/MES30004E/lego-element-lookup/issues"
#define AppUpdatesURL "https://github.com/MES30004E/lego-element-lookup/releases"
#define AppIcon "..\..\assets\icon.ico"
#define WizardLargeImage "..\..\assets\installer\windows\wizard-large.bmp"
#define WizardSmallImage "..\..\assets\installer\windows\wizard-small.bmp"

[Setup]
AppId={{A252F0AE-799B-4930-81BE-7CE34EC725AE}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppSupportURL}
AppUpdatesURL={#AppUpdatesURL}
DefaultDirName={localappdata}\Programs\LEGO Element Lookup
DefaultGroupName=LEGO Element Lookup
OutputDir=..\..\dist
OutputBaseFilename=LEGO-Element-Lookup-v{#AppVersion}-Windows-x86_64-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\LEGO Element Lookup.exe
UninstallDisplayName={#AppName}
SetupIconFile={#AppIcon}
LicenseFile=..\..\LICENSE
WizardImageFile={#WizardLargeImage}
WizardSmallImageFile={#WizardSmallImage}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
; Restart Manager detects a running app and requests a clean close; it never force-closes it.
CloseApplications=yes
RestartApplications=no
; User configuration and caches live outside {app}; neither upgrades nor uninstall delete them.

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\LEGO Element Lookup"; Filename: "{app}\LEGO Element Lookup.exe"
Name: "{autodesktop}\LEGO Element Lookup"; Filename: "{app}\LEGO Element Lookup.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\LEGO Element Lookup.exe"; Description: "Launch LEGO Element Lookup"; Flags: nowait postinstall skipifsilent
