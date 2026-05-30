# AGENTS.md

## Cursor Cloud specific instructions

### Product

Single **Windows desktop** app (Python 3.11+, PySide6): **AzerothCore Launcher** — GUI to start/stop MySQL, authserver, worldserver, and Ollama with embedded terminals. Not a monorepo. There is no Docker stack, CI workflow, or automated test suite in this repository.

### Platform expectations

| Environment | Full `python main.py` | Practical cloud-agent work |
|-------------|----------------------|----------------------------|
| **Windows 10/11** | Yes (see README) | Run launcher, PyInstaller `build.bat`, full E2E with AzerothCore binaries |
| **Linux (this VM)** | **No** — `main.py` imports `WINFUNCTYPE` / `windll`; `core/process_manager.py` requires `pywinpty` (Windows ConPTY). `pywinpty` does not build on Linux. | `compileall`, PySide6 + `ui/theme.qss` / asset smoke tests, static review |

External AzerothCore server binaries are **not** in the repo; configure paths in Settings (`%APPDATA%\AzerothCore Launcher\config.json` on Windows).

### One-time system packages (Linux GUI smoke tests)

Not covered by the VM update script. Install if PySide6 cannot load a platform plugin:

```bash
sudo apt-get install -y python3.12-venv xvfb libxcb-cursor0 libxcb-xinerama0 libxkbcommon-x11-0 libegl1
```

For headless Qt checks, prefer `QT_QPA_PLATFORM=offscreen` (works without a working `xcb` plugin in this image).

On **Windows**, use README: `python -m venv .venv`, `.venv\Scripts\activate`, `pip install -r requirements.txt`, then `python main.py`.

### Run / build (Windows)

From README:

- **Dev:** `python main.py` after `pip install -r requirements.txt`
- **Release:** `build.bat` → `dist\AzerothCore Launcher.exe`

### Lint / tests

No project linter config, pre-commit hooks, or unit tests. Use:

```bash
.venv/bin/python -m compileall -q core ui main.py
```

### Linux smoke test (dependencies + UI assets)

After the update script:

```bash
cd /workspace
QT_QPA_PLATFORM=offscreen .venv/bin/python -c "
from PySide6.QtWidgets import QApplication
from ui.logo import make_window_icon
from core.paths import resource_path
app = QApplication([])
app.setStyleSheet(resource_path('ui','theme.qss').read_text(encoding='utf-8'))
assert not make_window_icon().isNull()
print('OK')
"
```

### Services (full E2E on Windows only)

| Service | Required for full server E2E |
|---------|------------------------------|
| Launcher GUI | MUST |
| MySQL (`mysqld.exe`) | MUST |
| `authserver.exe` / `worldserver.exe` | MUST |
| Ollama | Optional |
| WoW client | Optional |

Default MySQL port in config: **3306**.
