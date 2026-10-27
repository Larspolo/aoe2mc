; The Windows installer (#1542): a per-user install of the app bundle dist\aoe2mc (no admin rights), a Start menu item
; and an uninstaller. Build: iscc /DVERSION=1.2.3 packaging\windows.iss (after PyInstaller and packaging\icon.py).
#ifndef VERSION
  #define VERSION "0.0.0"
#endif

[Setup]
AppId=io.github.larspolo.aoe2mc
AppName=aoe2mc
AppVersion={#VERSION}
AppPublisher=Larspolo
AppPublisherURL=https://github.com/Larspolo/aoe2mc
DefaultDirName={localappdata}\Programs\aoe2mc
DefaultGroupName=aoe2mc
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=aoe2mc-{#VERSION}-windows-x64-setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\aoe2mc-gui.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "..\dist\aoe2mc\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\aoe2mc"; Filename: "{app}\aoe2mc-gui.exe"
Name: "{group}\Uninstall aoe2mc"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\aoe2mc-gui.exe"; Description: "Start aoe2mc"; Flags: nowait postinstall skipifsilent
