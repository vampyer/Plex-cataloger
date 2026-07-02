Plex Cataloger - Installer build instructions

This project includes an Inno Setup script to create a Windows installer that installs the packaged application and ensures an `instance` folder is created next to the executable (where the DB and secret key live).

Prerequisites
- PyInstaller build of the app (one-dir) located in `dist\PlexCataloger` (run `python -m PyInstaller --noconfirm --onedir --name "PlexCataloger" --add-data "templates;templates" --add-data "static;static" main.py`)
- Inno Setup (https://jrsoftware.org/) installed (ISCC.exe available in PATH or default Program Files location)

Build steps
1. Ensure `dist\PlexCataloger` exists and contains `PlexCataloger.exe` and supporting files.
2. Run the installer build script (PowerShell):

```powershell
# from project root
installer\build_installer.ps1
```

or run Inno Setup directly using the provided script `PlexCatalogerInstaller.iss` in the project root using the Inno Setup Compiler (ISCC.exe):

```powershell
ISCC.exe PlexCatalogerInstaller.iss
```

Output
- The installer `PlexCataloger_Installer.exe` will be produced in the `dist` folder.

Icon generation and embedding
- Generate icons before building the installer (creates `assets/icons/plex_cataloger.ico`):
	```powershell
	python tools/generate_icon.py
	```
- Embed the icon into the EXE when building the PyInstaller bundle by adding the `--icon` flag:
	```powershell
	python -m PyInstaller --noconfirm --onedir --name "PlexCataloger" --icon assets\icons\plex_cataloger.ico --add-data "templates;templates" --add-data "static;static" main.py
	```

Installer behavior
- Installs files into %ProgramFiles%\PlexCataloger by default.
- Creates an `instance` directory next to the EXE so runtime DB (`plex_catalog.db`) and the encryption key (`secret.key`) will be created there on first run.
- Adds Start Menu and Desktop shortcuts and an option to launch the app after installation.

Security note
- The `instance\secret.key` file is the Fernet key used to encrypt stored Plex tokens. Keep it secure — anyone with access to this key can decrypt tokens stored in the DB.
