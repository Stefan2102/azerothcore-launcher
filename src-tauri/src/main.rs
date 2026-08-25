// Release builds are desktop applications and must not allocate a separate
// console host. Debug builds keep their console for Rust diagnostics.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    azerothcore_launcher_lib::run();
}
