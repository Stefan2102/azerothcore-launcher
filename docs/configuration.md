# Configuration

## Location and lifecycle

The launcher creates `%APPDATA%\AzerothCore Launcher\config.json` on first run and opens Settings automatically. The configuration schema is defined below.

Saving is atomic. If an existing file is malformed or unreadable, initialization reports the error instead of silently replacing user data.

## Fields

| JSON field | Default | Purpose |
| --- | --- | --- |
| `sql_host` | `127.0.0.1` | Host passed to `mysqladmin`. |
| `sql_port` | `3306` | Port passed to `mysqladmin`. |
| `sql_user` | `acore` | User passed to `mysqladmin`. |
| `sql_password_encrypted` | DPAPI value for `acore` | Current-user encrypted SQL password. |
| `client_path` | empty | World of Warcraft executable. |
| `mysql_path` | `.\mysql\bin\mysqld.exe` | MySQL server executable. |
| `auth_server_path` | `.\authserver.exe` | AzerothCore Authserver executable. |
| `world_server_path` | `.\worldserver.exe` | AzerothCore Worldserver executable. |
| `settings_completed` | `false` | Controls automatic first-run Settings display. |

The Settings UI presents the connection, client, and server executable values as three concise sections inside a native WebView2 modal. It works with a plain `sqlPassword` field, but only the encrypted value is written to JSON. The launcher uses a fixed Icy Blue palette.

Rust owns configuration normalization at the typed IPC boundary. Leading and trailing whitespace is removed from host, user, and path values; empty host, user, and service paths receive the defaults above. Port `0` receives the default `3306`, while other out-of-range values are clamped to the valid `1`–`65535` range. `settings_completed` is not editable or returned by the Settings command; it remains internal and is exposed only as the initialization snapshot's `needsFirstRunSetup` decision.

## Path rules

Absolute paths are used directly. Relative paths resolve from the release executable's directory; development runs resolve them from the directory used to start Tauri.

MySQL uses the directory above `bin` as its working directory when `mysqld.exe` is located in a `bin` directory. Authserver, Worldserver, and the WoW client run from their executable directories. Ollama is discovered from `PATH` and has no configured path.

## Troubleshooting

- **Executable not found:** select the exact `.exe`, not only its containing directory.
- **Ollama was not found:** restart the launcher after adding Ollama to `PATH`.
- **mysqladmin shutdown failed:** verify host, port, user, password, and that `mysqladmin.exe` is beside `mysqld.exe`.
- **Password cannot be decrypted:** DPAPI data normally decrypts only for the Windows user and computer that created it. Re-enter and save the password on the current account.
- **Blank application window:** repair or install the Microsoft Edge WebView2 Runtime.
