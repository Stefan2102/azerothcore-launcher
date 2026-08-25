use std::sync::Arc;

use tauri::ipc::Channel;
use tauri::{AppHandle, State};

use crate::models::{BackendEvent, LauncherSnapshot, ServiceId, SettingsInput, SettingsView};
use crate::runtime::LauncherRuntime;

#[tauri::command]
pub fn initialize(
    runtime: State<'_, Arc<LauncherRuntime>>,
    on_event: Channel<BackendEvent>,
) -> Result<LauncherSnapshot, String> {
    runtime.initialize(on_event).map_err(to_message)
}

#[tauri::command]
pub fn load_settings(runtime: State<'_, Arc<LauncherRuntime>>) -> Result<SettingsView, String> {
    runtime.load_settings().map_err(to_message)
}

#[tauri::command]
pub fn save_settings(
    runtime: State<'_, Arc<LauncherRuntime>>,
    settings: SettingsInput,
) -> Result<SettingsView, String> {
    runtime.save_settings(settings).map_err(to_message)
}

#[tauri::command]
pub fn validate_executable_path(runtime: State<'_, Arc<LauncherRuntime>>, value: String) -> bool {
    runtime.validate_path(&value)
}

#[tauri::command]
pub fn start_service(
    runtime: State<'_, Arc<LauncherRuntime>>,
    service_id: ServiceId,
    columns: u16,
    rows: u16,
) -> Result<(), String> {
    runtime
        .inner()
        .start_service(service_id, columns, rows)
        .map_err(to_message)
}

#[tauri::command]
pub fn stop_service(
    runtime: State<'_, Arc<LauncherRuntime>>,
    service_id: ServiceId,
) -> Result<(), String> {
    runtime.inner().stop_service(service_id).map_err(to_message)
}

#[tauri::command]
pub fn write_service(
    runtime: State<'_, Arc<LauncherRuntime>>,
    service_id: ServiceId,
    text: String,
) -> Result<(), String> {
    runtime.write_service(service_id, &text).map_err(to_message)
}

#[tauri::command]
pub fn write_terminal_input(
    runtime: State<'_, Arc<LauncherRuntime>>,
    service_id: ServiceId,
    data: String,
) -> Result<(), String> {
    runtime
        .write_terminal_input(service_id, &data)
        .map_err(to_message)
}

#[tauri::command]
pub fn resize_service(
    runtime: State<'_, Arc<LauncherRuntime>>,
    service_id: ServiceId,
    columns: u16,
    rows: u16,
) -> Result<(), String> {
    runtime
        .resize_service(service_id, columns, rows)
        .map_err(to_message)
}

#[tauri::command]
pub fn launch_world_of_warcraft(runtime: State<'_, Arc<LauncherRuntime>>) -> Result<(), String> {
    runtime.launch_world_of_warcraft().map_err(to_message)
}

#[tauri::command]
pub fn running_services(runtime: State<'_, Arc<LauncherRuntime>>) -> Vec<ServiceId> {
    runtime.running_services()
}

#[tauri::command]
pub fn exit_application(
    app: AppHandle,
    runtime: State<'_, Arc<LauncherRuntime>>,
    force: bool,
) -> Result<(), String> {
    let running = runtime.running_services();
    if !force && !running.is_empty() {
        return Err("Services are still running.".to_owned());
    }
    runtime.shutdown_all();
    app.exit(0);
    Ok(())
}

fn to_message(error: impl std::fmt::Display) -> String {
    error.to_string()
}
