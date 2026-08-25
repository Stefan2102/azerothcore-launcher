mod commands;
mod config;
mod error;
mod models;
mod paths;
mod runtime;
mod secrets;
mod service;
mod window_icon;

use std::sync::{
    Arc,
    atomic::{AtomicBool, Ordering},
};

use tauri::{Manager, RunEvent, WindowEvent};
use windows::Win32::UI::WindowsAndMessaging::{MB_ICONERROR, MB_OK, MessageBoxW};
use windows::core::PCWSTR;

use crate::config::ConfigManager;
use crate::error::{LauncherError, LauncherResult};
use crate::paths::{appdata_config_path, launcher_base_dir};
use crate::runtime::LauncherRuntime;

const APPLICATION_NAME: &str = "AzerothCore Launcher";

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    if let Err(error) = run_application() {
        show_fatal_startup_error(&error);
    }
}

fn run_application() -> LauncherResult<()> {
    let config_path = appdata_config_path()?;
    let base_dir = launcher_base_dir()?;
    let runtime = LauncherRuntime::new(ConfigManager::new(config_path), base_dir);

    let application = tauri::Builder::default()
        // Single-instance must be first so no later plugin observes the secondary process.
        .plugin(tauri_plugin_single_instance::init(
            |app, _arguments, _cwd| {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.unminimize();
                    let _ = window.show();
                    let _ = window.maximize();
                    let _ = window.set_focus();
                }
            },
        ))
        .plugin(tauri_plugin_dialog::init())
        .manage(Arc::clone(&runtime))
        .setup(|app| {
            let window = app.get_webview_window("main").ok_or_else(|| {
                LauncherError::message("The main window is unavailable during icon setup.")
            })?;
            window_icon::apply(&window)?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::initialize,
            commands::load_settings,
            commands::save_settings,
            commands::validate_executable_path,
            commands::start_service,
            commands::stop_service,
            commands::write_service,
            commands::write_terminal_input,
            commands::resize_service,
            commands::launch_world_of_warcraft,
            commands::running_services,
            commands::exit_application,
        ])
        .build(tauri::generate_context!())
        .map_err(|error| LauncherError::message(format!("Tauri startup failed: {error}")))?;

    let icon_refresh_error_reported = AtomicBool::new(false);
    application.run(move |app, event| match event {
        RunEvent::Exit => runtime.shutdown_all(),
        RunEvent::WindowEvent {
            label,
            event: WindowEvent::ScaleFactorChanged { .. },
            ..
        } if label == "main" => {
            if let Some(window) = app.get_webview_window("main")
                && let Err(error) = window_icon::apply(&window)
                && !icon_refresh_error_reported.swap(true, Ordering::Relaxed)
            {
                show_native_error(
                    APPLICATION_NAME,
                    &format!("The taskbar icon could not be refreshed.\n\n{error}"),
                );
            }
        }
        _ => {}
    });
    Ok(())
}

fn fatal_startup_message(error: &LauncherError) -> String {
    format!("{APPLICATION_NAME} could not start.\n\n{error}")
}

fn show_fatal_startup_error(error: &LauncherError) {
    show_native_error(APPLICATION_NAME, &fatal_startup_message(error));
}

fn show_native_error(title: &str, message: &str) {
    let title = wide_string(title);
    let message = wide_string(message);

    // Keep native integration errors visible even when no webview is available;
    // this GUI-subsystem process has no console to receive diagnostics.
    unsafe {
        MessageBoxW(
            None,
            PCWSTR(message.as_ptr()),
            PCWSTR(title.as_ptr()),
            MB_OK | MB_ICONERROR,
        );
    }
}

fn wide_string(value: &str) -> Vec<u16> {
    value.encode_utf16().chain(std::iter::once(0)).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fatal_startup_message_identifies_the_application_and_cause() {
        let message = fatal_startup_message(&LauncherError::message("AppData is unavailable."));

        assert_eq!(
            message,
            "AzerothCore Launcher could not start.\n\nAppData is unavailable."
        );
    }

    #[test]
    fn win32_strings_are_null_terminated() {
        let encoded = wide_string("ice");

        assert_eq!(encoded.last(), Some(&0));
        assert_eq!(&encoded[..encoded.len() - 1], &[105, 99, 101]);
    }
}
