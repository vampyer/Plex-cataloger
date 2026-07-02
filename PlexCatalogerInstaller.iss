; Inno Setup script to install Plex Cataloger
[Setup]
AppName=Plex Cataloger
AppVersion=1.2b
DefaultDirName={localappdata}\PlexCataloger
DefaultGroupName=Plex Cataloger
OutputBaseFilename=PlexCataloger_Installer
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64os
OutputDir=dist
PrivilegesRequired=lowest
; Use the built icon for the installer window
SetupIconFile=assets\icons\plex_cataloger.ico

[Files]
Source: "dist\PlexCataloger.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Plex Cataloger"; Filename: "{app}\PlexCataloger.exe"; IconFilename: "{app}\PlexCataloger.exe"

[Run]
Filename: "{app}\PlexCataloger.exe"; Description: "Launch Plex Cataloger"; Flags: nowait postinstall skipifsilent
