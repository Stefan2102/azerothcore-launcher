# AzerothCore Launcher

Windows desktop launcher for [AzerothCore](https://www.azerothcore.org/) servers. Start and stop MySQL, Authserver, Worldserver, and Ollama from one application, with live terminal output for each service.

## Features

- Four integrated terminals (MySQL, Authserver, Worldserver, Ollama)
- Start and stop services from the sidebar
- Worldserver command input console commands
- Settings for database credentials and executable paths
- Launch World of Warcraft from the sidebar
- Single-instance application

## Requirements

- Windows 10/11 (64-bit)
- Python 3.11 or newer (for building or running from source)
- AzerothCore server binaries configured in Settings
- Ollama on `PATH` (optional, for the Ollama panel)

## Build

```bat
git clone https://github.com/Stefan2102/azerothcore-launcher.git
cd azerothcore-launcher
build.bat
```

The executable is written to `dist\AzerothCore Launcher.exe`.

## Run from source

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Configuration

On first launch, open **Settings** and set:

- SQL connection (used for MySQL shutdown via `mysqladmin`)
- Paths to `mysqld.exe`, `authserver.exe`, and `worldserver.exe`
- World of Warcraft client executable

Settings are stored in `%APPDATA%\AzerothCore Launcher\config.json`. Paths may be relative to the launcher working directory.

## Stopping services

| Service | Method |
|---------|--------|
| Worldserver | `server shutdown 1` |
| Authserver | Ctrl+C |
| MySQL | `mysqladmin shutdown` |
| Ollama | Ctrl+C |

## Disclaimer

Community tool for self-hosted AzerothCore servers. Not affiliated with Blizzard Entertainment or the AzerothCore project. World of Warcraft is a trademark of Blizzard Entertainment.

## License

Public domain — see [LICENSE](LICENSE) ([Unlicense](https://unlicense.org)).
