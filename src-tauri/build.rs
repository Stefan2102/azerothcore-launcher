fn main() {
    // The raw no-bundle build links the Windows icon through a generated
    // resource library. Watch the ICO explicitly so Cargo cannot reuse a stale
    // resource library after branding changes without Rust source changes.
    println!("cargo:rerun-if-changed=icons/icon.ico");
    tauri_build::build()
}
