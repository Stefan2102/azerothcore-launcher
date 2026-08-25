use std::os::windows::ffi::OsStrExt;
use std::path::Path;

use windows::Win32::Foundation::{FreeLibrary, HINSTANCE};
use windows::Win32::System::LibraryLoader::{
    LOAD_LIBRARY_AS_DATAFILE_EXCLUSIVE, LOAD_LIBRARY_AS_IMAGE_RESOURCE, LoadLibraryExW,
};
use windows::Win32::UI::HiDpi::GetSystemMetricsForDpi;
use windows::Win32::UI::WindowsAndMessaging::{
    IDI_APPLICATION, IMAGE_ICON, LR_SHARED, LoadImageW, SM_CXICON, SM_CXSMICON, SM_CYICON,
    SM_CYSMICON,
};
use windows::core::PCWSTR;

fn wide_path(path: &Path) -> Vec<u16> {
    path.as_os_str()
        .encode_wide()
        .chain(std::iter::once(0))
        .collect()
}

#[test]
fn compiled_launcher_icon_loads_at_standard_and_scaled_dimensions() {
    let executable = Path::new(env!("CARGO_BIN_EXE_azerothcore-launcher"));
    let executable_path = wide_path(executable);
    let module = unsafe {
        LoadLibraryExW(
            PCWSTR(executable_path.as_ptr()),
            None,
            LOAD_LIBRARY_AS_DATAFILE_EXCLUSIVE | LOAD_LIBRARY_AS_IMAGE_RESOURCE,
        )
    }
    .expect("compiled launcher should open as a resource module");
    let instance = HINSTANCE(module.0);

    for dpi in [96, 144, 192] {
        for (width_metric, height_metric) in [(SM_CXSMICON, SM_CYSMICON), (SM_CXICON, SM_CYICON)] {
            let width = unsafe { GetSystemMetricsForDpi(width_metric, dpi) };
            let height = unsafe { GetSystemMetricsForDpi(height_metric, dpi) };
            assert!(width > 0 && height > 0);

            let icon = unsafe {
                LoadImageW(
                    Some(instance),
                    IDI_APPLICATION,
                    IMAGE_ICON,
                    width,
                    height,
                    LR_SHARED,
                )
            }
            .expect("compiled icon resource should load at the system-requested size");
            assert!(!icon.0.is_null());
        }
    }

    unsafe { FreeLibrary(module) }.expect("resource module should close cleanly");
}
