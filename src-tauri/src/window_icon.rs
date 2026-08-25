use tauri::WebviewWindow;
use windows::Win32::Foundation::{HANDLE, HINSTANCE, HWND, LPARAM, WPARAM};
use windows::Win32::System::LibraryLoader::GetModuleHandleW;
use windows::Win32::UI::HiDpi::{GetDpiForWindow, GetSystemMetricsForDpi};
use windows::Win32::UI::WindowsAndMessaging::{
    ICON_BIG, ICON_SMALL, IDI_APPLICATION, IMAGE_ICON, LR_SHARED, LoadImageW, SM_CXICON,
    SM_CXSMICON, SM_CYICON, SM_CYSMICON, SYSTEM_METRICS_INDEX, SendMessageW, WM_SETICON,
};

use crate::error::{LauncherError, LauncherResult};

const DEFAULT_DPI: u32 = 96;

#[derive(Clone, Copy)]
enum IconRole {
    Small,
    Large,
}

impl IconRole {
    fn metrics(self) -> (SYSTEM_METRICS_INDEX, SYSTEM_METRICS_INDEX) {
        match self {
            Self::Small => (SM_CXSMICON, SM_CYSMICON),
            Self::Large => (SM_CXICON, SM_CYICON),
        }
    }

    fn message_parameter(self) -> u32 {
        match self {
            Self::Small => ICON_SMALL,
            Self::Large => ICON_BIG,
        }
    }
}

pub(crate) fn apply(window: &WebviewWindow) -> LauncherResult<()> {
    let hwnd = window.hwnd().map_err(|error| {
        LauncherError::message(format!("Could not access the main window: {error}"))
    })?;

    // Tauri currently exposes its HWND through windows 0.61 while the launcher
    // uses windows 0.62. Both wrappers contain the same native pointer, so keep
    // the version boundary isolated here instead of leaking it through the API.
    apply_to_hwnd(HWND(hwnd.0))
}

fn apply_to_hwnd(hwnd: HWND) -> LauncherResult<()> {
    // Tauri 2.11 decodes only the first ICO entry for its default runtime icon
    // and assigns it as ICON_SMALL. Loading the compiled resource directly lets
    // Windows select the best ICO frame for each DPI-aware native icon size.
    let dpi = unsafe { GetDpiForWindow(hwnd) };
    let dpi = if dpi == 0 { DEFAULT_DPI } else { dpi };
    let module = current_module()?;

    for role in [IconRole::Small, IconRole::Large] {
        let icon = load_application_icon(module, dpi, role)?;

        unsafe {
            SendMessageW(
                hwnd,
                WM_SETICON,
                Some(WPARAM(role.message_parameter() as usize)),
                Some(LPARAM(icon.0 as isize)),
            );
        }
    }

    Ok(())
}

fn current_module() -> LauncherResult<HINSTANCE> {
    let module = unsafe { GetModuleHandleW(None) }.map_err(|error| {
        LauncherError::message(format!("Could not access the application module: {error}"))
    })?;
    Ok(HINSTANCE(module.0))
}

fn load_application_icon(module: HINSTANCE, dpi: u32, role: IconRole) -> LauncherResult<HANDLE> {
    let (width_metric, height_metric) = role.metrics();
    let width = unsafe { GetSystemMetricsForDpi(width_metric, dpi) };
    let height = unsafe { GetSystemMetricsForDpi(height_metric, dpi) };

    if width <= 0 || height <= 0 {
        return Err(LauncherError::message(format!(
            "Windows returned an invalid icon size ({width}x{height}) for {dpi} DPI."
        )));
    }

    // LR_SHARED makes Windows own and cache the returned resource handle. It
    // must not be destroyed by the launcher and remains valid for the process.
    unsafe {
        LoadImageW(
            Some(module),
            IDI_APPLICATION,
            IMAGE_ICON,
            width,
            height,
            LR_SHARED,
        )
    }
    .map_err(|error| {
        LauncherError::message(format!(
            "Could not load the {width}x{height} application icon: {error}"
        ))
    })
}
