use std::ffi::OsString;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

#[cfg(windows)]
use std::os::windows::process::CommandExt;

use crate::error::{LauncherError, LauncherResult};
use crate::models::{LauncherConfig, ServiceId};
use crate::paths::resolve_config_path;

const DETACHED_PROCESS: u32 = 0x0000_0008;
const CREATE_NEW_PROCESS_GROUP: u32 = 0x0000_0200;

#[derive(Debug, Clone)]
pub struct ServiceDefinition {
    // Definitions are data rather than arbitrary command strings. Keeping the
    // program and arguments separate prevents shell interpretation.
    pub program: OsString,
    pub arguments: Vec<OsString>,
    pub working_directory: Option<PathBuf>,
}

#[derive(Debug, Clone)]
pub struct MysqlShutdownDefinition {
    pub program: PathBuf,
    pub arguments: Vec<OsString>,
    pub working_directory: PathBuf,
    pub password: String,
}

pub fn build_service_definition(
    service_id: ServiceId,
    config: &LauncherConfig,
    base_dir: &Path,
) -> LauncherResult<ServiceDefinition> {
    match service_id {
        ServiceId::Mysql => {
            let binary =
                required_executable(base_dir, &config.mysql_path, "MySQL path (mysqld.exe)")?;
            let working_directory = mysql_root(&binary);
            // Running from the install root preserves relative MySQL paths while
            // --console keeps diagnostics attached to the managed PTY.
            Ok(ServiceDefinition {
                program: binary.into_os_string(),
                arguments: vec![OsString::from("--console")],
                working_directory: Some(working_directory),
            })
        }
        ServiceId::Authserver => {
            executable_service(base_dir, &config.auth_server_path, "Auth Server path")
        }
        ServiceId::Worldserver => {
            executable_service(base_dir, &config.world_server_path, "World Server path")
        }
        ServiceId::Ollama => {
            // Resolve PATH once and launch the concrete executable directly;
            // no command shell is introduced into the privileged backend.
            let executable = which::which("ollama").map_err(|_| {
                LauncherError::message(
                    "Ollama was not found on PATH. Install Ollama or add it to PATH.",
                )
            })?;
            Ok(ServiceDefinition {
                program: executable.into_os_string(),
                arguments: vec![OsString::from("serve")],
                working_directory: None,
            })
        }
    }
}

pub fn build_mysql_shutdown_definition(
    config: &LauncherConfig,
    base_dir: &Path,
    password: String,
) -> LauncherResult<MysqlShutdownDefinition> {
    let mysqld = required_executable(base_dir, &config.mysql_path, "MySQL path (mysqld.exe)")?;
    let mysqladmin = mysqld
        .parent()
        .ok_or_else(|| LauncherError::message("MySQL executable has no parent directory."))?
        .join("mysqladmin.exe");
    required_file(&mysqladmin, "mysqladmin.exe")?;

    Ok(MysqlShutdownDefinition {
        program: mysqladmin,
        arguments: vec![
            OsString::from("-h"),
            OsString::from(&config.sql_host),
            OsString::from("-P"),
            OsString::from(config.sql_port.to_string()),
            OsString::from("-u"),
            OsString::from(&config.sql_user),
            OsString::from("shutdown"),
        ],
        working_directory: mysql_root(&mysqld),
        // The caller transfers this value through MYSQL_PWD, never arguments.
        password,
    })
}

pub fn launch_world_of_warcraft(config: &LauncherConfig, base_dir: &Path) -> LauncherResult<()> {
    if config.client_path.trim().is_empty() {
        return Err(LauncherError::message("Client Path is not configured."));
    }
    let binary = resolve_config_path(base_dir, &config.client_path);
    required_file(&binary, "World of Warcraft executable")?;
    let working_directory = binary.parent().ok_or_else(|| {
        LauncherError::message("World of Warcraft executable has no parent directory.")
    })?;

    let mut command = Command::new(&binary);
    command
        .current_dir(working_directory)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    #[cfg(windows)]
    // The game must outlive the launcher and must not inherit its console group.
    command.creation_flags(DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP);
    command.spawn().map_err(|error| {
        LauncherError::message(format!("Failed to launch World of Warcraft: {error}"))
    })?;
    Ok(())
}

fn executable_service(
    base_dir: &Path,
    value: &str,
    label: &str,
) -> LauncherResult<ServiceDefinition> {
    let binary = required_executable(base_dir, value, label)?;
    let working_directory = binary
        .parent()
        .ok_or_else(|| LauncherError::message(format!("{label} has no parent directory.")))?
        .to_path_buf();
    Ok(ServiceDefinition {
        program: binary.into_os_string(),
        arguments: Vec::new(),
        working_directory: Some(working_directory),
    })
}

fn required_executable(base_dir: &Path, value: &str, label: &str) -> LauncherResult<PathBuf> {
    if value.trim().is_empty() {
        return Err(LauncherError::message(format!(
            "{label} is not configured."
        )));
    }
    let path = resolve_config_path(base_dir, value);
    required_file(&path, label)?;
    Ok(path)
}

fn required_file(path: &Path, label: &str) -> LauncherResult<()> {
    if path.is_file() {
        Ok(())
    } else {
        Err(LauncherError::message(format!(
            "{label} not found: {}",
            path.display()
        )))
    }
}

fn mysql_root(binary: &Path) -> PathBuf {
    // Common portable distributions place tools in <root>\bin but resolve
    // configuration and data relative to <root>.
    let parent = binary.parent().unwrap_or_else(|| Path::new("."));
    if parent
        .file_name()
        .is_some_and(|name| name.eq_ignore_ascii_case("bin"))
    {
        parent.parent().unwrap_or(parent).to_path_buf()
    } else {
        parent.to_path_buf()
    }
}

#[cfg(test)]
mod tests {
    use std::fs;

    use super::*;

    #[test]
    fn mysql_runs_from_install_root_with_console_output() {
        let directory = tempfile::tempdir().expect("temporary directory");
        let binary = directory
            .path()
            .join("mysql")
            .join("bin")
            .join("mysqld.exe");
        fs::create_dir_all(binary.parent().expect("binary parent")).expect("create bin directory");
        fs::write(&binary, []).expect("create executable fixture");
        let config = LauncherConfig {
            mysql_path: binary.to_string_lossy().into_owned(),
            ..LauncherConfig::default()
        };

        let definition = build_service_definition(ServiceId::Mysql, &config, directory.path())
            .expect("mysql definition");

        assert_eq!(definition.arguments, [OsString::from("--console")]);
        assert_eq!(
            definition.working_directory,
            Some(directory.path().join("mysql"))
        );
    }

    #[test]
    fn missing_server_executable_returns_a_descriptive_error() {
        let config = LauncherConfig::default();
        let error =
            build_service_definition(ServiceId::Authserver, &config, Path::new(r"C:\launcher"))
                .expect_err("missing executable should fail");
        assert!(error.to_string().contains("Auth Server path not found"));
    }
}
