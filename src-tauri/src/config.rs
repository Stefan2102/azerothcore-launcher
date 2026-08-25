use std::fs;
use std::io::Write;
use std::path::PathBuf;

#[cfg(test)]
use std::path::Path;

use tempfile::NamedTempFile;

use crate::error::{LauncherError, LauncherResult};
use crate::models::{LauncherConfig, SettingsInput, SettingsView};
use crate::secrets::{decrypt_password, encrypt_password};

#[derive(Debug, Clone)]
pub struct ConfigManager {
    path: PathBuf,
}

impl ConfigManager {
    pub fn new(path: PathBuf) -> Self {
        Self { path }
    }

    #[cfg(test)]
    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn ensure_exists(&self) -> LauncherResult<()> {
        if self.path.exists() {
            return Ok(());
        }
        // First-run defaults still pass through DPAPI; plaintext credentials are
        // never written merely because the settings screen has not opened yet.
        let config = LauncherConfig {
            sql_password_encrypted: encrypt_password("acore")?,
            ..LauncherConfig::default()
        };
        self.save_config(&config)
    }

    pub fn load_config(&self) -> LauncherResult<LauncherConfig> {
        self.ensure_exists()?;
        let contents = fs::read_to_string(&self.path).map_err(|error| {
            LauncherError::message(format!("Failed to read {}: {error}", self.path.display()))
        })?;
        serde_json::from_str(&contents).map_err(|error| {
            LauncherError::message(format!(
                "Invalid configuration in {}: {error}",
                self.path.display()
            ))
        })
    }

    pub fn load_settings(&self) -> LauncherResult<SettingsView> {
        let config = self.load_config()?;
        // Decryption occurs only at the typed settings boundary. The runtime
        // otherwise keeps the persisted encrypted payload opaque.
        Ok(SettingsView {
            sql_host: config.sql_host,
            sql_port: config.sql_port,
            sql_user: config.sql_user,
            sql_password: decrypt_password(&config.sql_password_encrypted)?,
            client_path: config.client_path,
            mysql_path: config.mysql_path,
            auth_server_path: config.auth_server_path,
            world_server_path: config.world_server_path,
        })
    }

    pub fn save_settings(&self, settings: SettingsInput) -> LauncherResult<SettingsView> {
        // Build a fresh value instead of mutating the old document so removed or
        // unknown fields cannot silently survive a save.
        let config = LauncherConfig {
            sql_host: nonempty_or(settings.sql_host, "127.0.0.1"),
            sql_port: normalize_port(settings.sql_port),
            sql_user: nonempty_or(settings.sql_user, "acore"),
            sql_password_encrypted: encrypt_password(&settings.sql_password)?,
            client_path: settings.client_path.trim().to_owned(),
            mysql_path: nonempty_or(settings.mysql_path, r".\mysql\bin\mysqld.exe"),
            auth_server_path: nonempty_or(settings.auth_server_path, r".\authserver.exe"),
            world_server_path: nonempty_or(settings.world_server_path, r".\worldserver.exe"),
            settings_completed: true,
        };
        self.save_config(&config)?;
        self.load_settings()
    }

    pub fn save_config(&self, config: &LauncherConfig) -> LauncherResult<()> {
        let parent = self
            .path
            .parent()
            .ok_or_else(|| LauncherError::message("Configuration path has no parent directory."))?;
        fs::create_dir_all(parent)?;

        let payload = serde_json::to_string_pretty(config)? + "\n";
        // The temporary file lives beside the destination. After flushing it to
        // disk, persist performs a same-volume atomic replacement on Windows.
        let mut temporary = NamedTempFile::new_in(parent)?;
        temporary.write_all(payload.as_bytes())?;
        temporary.as_file().sync_all()?;
        temporary.persist(&self.path).map_err(|error| {
            LauncherError::message(format!(
                "Failed to atomically save {}: {}",
                self.path.display(),
                error.error
            ))
        })?;
        Ok(())
    }
}

fn nonempty_or(value: String, fallback: &str) -> String {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        fallback.to_owned()
    } else {
        trimmed.to_owned()
    }
}

fn normalize_port(value: i64) -> u16 {
    if value == 0 {
        3306
    } else {
        value.clamp(1, u16::MAX as i64) as u16
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn first_run_creates_defaults_and_marks_setup_incomplete() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let manager = ConfigManager::new(directory.path().join("config.json"));

        let settings = manager.load_settings().expect("default settings");

        assert_eq!(settings.sql_host, "127.0.0.1");
        assert_eq!(settings.sql_port, 3306);
        assert_eq!(settings.sql_user, "acore");
        assert_eq!(settings.sql_password, "acore");
        assert!(
            !manager
                .load_config()
                .expect("default config")
                .settings_completed
        );
    }

    #[test]
    fn save_settings_is_atomic_and_applies_empty_field_defaults() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let manager = ConfigManager::new(directory.path().join("config.json"));
        let saved = manager
            .save_settings(SettingsInput {
                sql_host: " ".to_owned(),
                sql_port: 3307,
                sql_user: " ".to_owned(),
                sql_password: "secret".to_owned(),
                client_path: " wow.exe ".to_owned(),
                mysql_path: String::new(),
                auth_server_path: String::new(),
                world_server_path: String::new(),
            })
            .expect("saved settings");

        assert_eq!(saved.sql_host, "127.0.0.1");
        assert_eq!(saved.sql_user, "acore");
        assert_eq!(saved.sql_password, "secret");
        assert_eq!(saved.client_path, "wow.exe");
        assert!(
            manager
                .load_config()
                .expect("saved config")
                .settings_completed
        );
        assert!(!manager.path().with_extension("tmp").exists());
    }

    #[test]
    fn save_settings_normalizes_port_at_the_native_boundary() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let manager = ConfigManager::new(directory.path().join("config.json"));

        for (input, expected) in [(0, 3306), (-5, 1), (70_000, 65_535)] {
            let saved = manager
                .save_settings(SettingsInput {
                    sql_host: String::new(),
                    sql_port: input,
                    sql_user: String::new(),
                    sql_password: String::new(),
                    client_path: String::new(),
                    mysql_path: String::new(),
                    auth_server_path: String::new(),
                    world_server_path: String::new(),
                })
                .expect("normalized settings");
            assert_eq!(saved.sql_port, expected);
        }
    }
}
