# Plex Cataloger

A web-based GUI application to import Plex metadata, display media with poster images, and export data for use on websites.

## Features

- Import movies and TV shows from a Plex server
- Automatic poster image downloading
- Browse catalog in a responsive grid layout
- Edit metadata (custom notes, website URLs, trailer links)
- Export in multiple formats: JSON, HTML, CSV
- Works as a local web application

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application with the internal browser window:
```bash
python main.py
```

3. The app will open in an embedded browser window. If that fails, it will fall back to your default system browser.

## Packaging as a single EXE

To bundle the app into one executable while keeping the SQLite database outside the EXE, use PyInstaller with the windowed subsystem and include only the app assets, not generated poster files:

```powershell
python -m PyInstaller --noconfirm --onefile --windowed --name "PlexCataloger" --icon assets\icons\plex_cataloger.ico --add-data "templates;templates" --add-data "static/css;static/css" --add-data "static/plex_cataloger.ico;static" main.py
```

The resulting one-file executable will be in `dist\PlexCataloger.exe` and the app will create `instance\plex_catalog.db` and `instance\posters` next to it.

> Note: poster images are stored externally in `instance\posters`, not inside the EXE.

## Usage

1. **Import from Plex**
   - Go to the Import page
   - Enter your Plex server URL and token
   - Select a specific library or leave blank for all
   - Click "Start Import"

2. **Manage Catalog**
   - View all imported items in the Catalog
   - Click any item to see details
   - Edit metadata, upload custom posters, add notes

3. **Export for Website**
   - Go to the Export page
   - Choose format: JSON, HTML, or CSV
   - Select which library to export
   - Download the generated file

## Export Formats

- **JSON**: Structured data for web applications
- **HTML**: Ready-to-use static webpage with posters
- **CSV**: Spreadsheet-compatible data

## Notes

- Plex tokens can be found in your Plex settings or by signing into plex.tv
- Poster images are stored in `instance/posters/`
- The SQLite database is `instance/plex_catalog.db`

## Packaging as a single EXE

To bundle the app into one executable while keeping the SQLite database and poster files external, use PyInstaller with the windowed subsystem and include only built assets:

```powershell
python -m PyInstaller --noconfirm --onefile --windowed --name "PlexCataloger" --icon assets\icons\plex_cataloger.ico --add-data "templates;templates" --add-data "static/css;static/css" --add-data "static/plex_cataloger.ico;static" main.py
```

The resulting one-file executable will appear at `dist\PlexCataloger.exe`.

At runtime, the app will create `instance\plex_catalog.db` and store generated poster images in `instance\posters` next to the executable. This makes the one-file EXE portable: you can move the `dist` folder to another machine and the app will keep its data locally.

## Portable ZIP distribution

Build a portable ZIP package that contains `PlexCataloger.exe` and can be extracted anywhere:

```powershell
powershell -ExecutionPolicy RemoteSigned -File .\build_portable.ps1
```

This creates two ZIP archives in `dist\`:

- `PlexCatalogerPortable_<timestamp>.zip` — executable package for portable use
- `PlexCatalogerSource_<timestamp>.zip` — source code archive for the project

Extract the portable ZIP, then run `PlexCataloger.exe`. Runtime data will be stored locally in `instance\` next to the executable.

## Optional installer build

If you still want a Windows installer, you can build it after creating `dist\PlexCataloger.exe`:

```powershell
powershell -ExecutionPolicy RemoteSigned -File .\installer\build_installer.ps1
```

This script looks for `ISCC.exe` in standard Inno Setup locations, in `PATH`, or in the local fallback at `installer\innosetup\ISCC.exe`.

The installer output is written to `dist\PlexCataloger_Installer.exe` or a timestamped filename.
