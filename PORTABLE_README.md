# Plex Cataloger Portable v1.2b

A portable Plex media library cataloger with GUI interface.

## Developer
Vampyer Knight 2026

## Quick Start

1. Extract this ZIP to any folder
2. Run `PlexCataloger.exe`
3. The app will open in a browser window

## Features

- Import movies and TV shows from Plex server
- Automatic poster image downloading
- Browse and edit catalog
- Export to JSON, HTML, or CSV formats
- HTML export includes posters in a `posters/` subfolder

## Directory Structure

```
PlexCataloger/
├── PlexCataloger.exe       # Main application
├── instance/             # Runtime data (created on first run)
│   ├── plex_catalog.db     # SQLite database
│   ├── secret.key          # Encryption key for stored tokens
│   ├── posters/            # Downloaded poster images
│   └── exports/            # Generated export files
└── templates/            # HTML templates (bundled in EXE)
```

## First Run

On first launch, the app creates an `instance` folder next to the EXE containing:
- `plex_catalog.db` - Your media catalog database
- `secret.key` - Encryption key (keep secure)
- `posters/` - Downloaded poster images
- `exports/` - Generated export files

## Building from Source

```powershell
python -m PyInstaller PlexCataloger.spec
```

Requires: Python 3.11+, Flask, pywebview, plexapi, cryptography

## License

MIT License