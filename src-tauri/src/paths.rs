use std::env;
use std::path::{Path, PathBuf};

use crate::error::{LauncherError, LauncherResult};

const APP_DIRECTORY_NAME: &str = "AzerothCore Launcher";

pub fn appdata_config_path() -> LauncherResult<PathBuf> {
    // APPDATA is authoritative on Windows. USERPROFILE is only a defensive
    // fallback for environments that omit the conventional roaming variable.
    let roaming = env::var_os("APPDATA")
        .map(PathBuf::from)
        .or_else(|| {
            env::var_os("USERPROFILE")
                .map(PathBuf::from)
                .map(|profile| profile.join("AppData").join("Roaming"))
        })
        .ok_or_else(|| {
            LauncherError::message("Windows roaming AppData directory is unavailable.")
        })?;
    Ok(roaming.join(APP_DIRECTORY_NAME).join("config.json"))
}

pub fn launcher_base_dir() -> LauncherResult<PathBuf> {
    // Development resolves paths from the project working directory, whereas a
    // distributed raw executable must remain portable with its adjacent files.
    if cfg!(debug_assertions) {
        return env::current_dir().map_err(Into::into);
    }

    let executable = env::current_exe()?;
    executable
        .parent()
        .map(Path::to_path_buf)
        .ok_or_else(|| LauncherError::message("Launcher executable directory is unavailable."))
}

pub fn resolve_config_path(base_dir: &Path, value: &str) -> PathBuf {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return PathBuf::new();
    }

    let path = PathBuf::from(trimmed);
    // Do not canonicalize here: settings validation must also produce a useful
    // resolved path when the configured file does not exist yet.
    if path.is_absolute() {
        path
    } else {
        base_dir.join(path)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn resolves_relative_paths_from_launcher_directory() {
        let base = Path::new(r"C:\launcher");
        assert_eq!(
            resolve_config_path(base, r".\authserver.exe"),
            base.join(r".\authserver.exe")
        );
    }

    #[test]
    fn keeps_absolute_paths_unchanged() {
        let absolute = r"D:\AzerothCore\authserver.exe";
        assert_eq!(
            resolve_config_path(Path::new(r"C:\launcher"), absolute),
            PathBuf::from(absolute)
        );
    }
}
