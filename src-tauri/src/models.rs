use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ServiceId {
    Mysql,
    Authserver,
    Worldserver,
    Ollama,
}

impl ServiceId {
    pub const ALL: [Self; 4] = [
        Self::Mysql,
        Self::Authserver,
        Self::Worldserver,
        Self::Ollama,
    ];

    pub const SHUTDOWN_ORDER: [Self; 4] = [
        Self::Worldserver,
        Self::Authserver,
        Self::Mysql,
        Self::Ollama,
    ];

    pub fn label(self) -> &'static str {
        match self {
            Self::Mysql => "MySQL",
            Self::Authserver => "Authserver",
            Self::Worldserver => "Worldserver",
            Self::Ollama => "Ollama",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ServiceState {
    Idle,
    Starting,
    Running,
    Stopping,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ServiceSnapshot {
    pub service_id: ServiceId,
    pub state: ServiceState,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct LauncherSnapshot {
    pub services: Vec<ServiceSnapshot>,
    pub needs_first_run_setup: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LauncherConfig {
    pub sql_host: String,
    pub sql_port: u16,
    pub sql_user: String,
    pub sql_password_encrypted: String,
    pub client_path: String,
    pub mysql_path: String,
    pub auth_server_path: String,
    pub world_server_path: String,
    pub settings_completed: bool,
}

impl Default for LauncherConfig {
    fn default() -> Self {
        Self {
            sql_host: "127.0.0.1".to_owned(),
            sql_port: 3306,
            sql_user: "acore".to_owned(),
            sql_password_encrypted: String::new(),
            client_path: String::new(),
            mysql_path: r".\mysql\bin\mysqld.exe".to_owned(),
            auth_server_path: r".\authserver.exe".to_owned(),
            world_server_path: r".\worldserver.exe".to_owned(),
            settings_completed: false,
        }
    }
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SettingsView {
    pub sql_host: String,
    pub sql_port: u16,
    pub sql_user: String,
    pub sql_password: String,
    pub client_path: String,
    pub mysql_path: String,
    pub auth_server_path: String,
    pub world_server_path: String,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct SettingsInput {
    pub sql_host: String,
    pub sql_port: i64,
    pub sql_user: String,
    pub sql_password: String,
    pub client_path: String,
    pub mysql_path: String,
    pub auth_server_path: String,
    pub world_server_path: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(
    tag = "event",
    content = "data",
    rename_all = "camelCase",
    rename_all_fields = "camelCase"
)]
pub enum BackendEvent {
    Output {
        service_id: ServiceId,
        text: String,
    },
    StateChanged {
        service_id: ServiceId,
        state: ServiceState,
    },
    Error {
        service_id: Option<ServiceId>,
        title: String,
        message: String,
    },
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn settings_view_serialization_contains_only_editable_values() {
        let view = SettingsView {
            sql_host: "127.0.0.1".to_owned(),
            sql_port: 3306,
            sql_user: "acore".to_owned(),
            sql_password: "secret".to_owned(),
            client_path: "wow.exe".to_owned(),
            mysql_path: "mysqld.exe".to_owned(),
            auth_server_path: "authserver.exe".to_owned(),
            world_server_path: "worldserver.exe".to_owned(),
        };

        let serialized = serde_json::to_value(view).expect("serialize settings view");
        let object = serialized.as_object().expect("settings object");

        assert_eq!(object.len(), 8);
        assert!(!object.contains_key("settingsCompleted"));
        assert!(!object.contains_key("resolvedPath"));
    }
}
