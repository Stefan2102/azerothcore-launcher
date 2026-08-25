use std::slice;

use base64::Engine;
use base64::engine::general_purpose::STANDARD;
use windows::Win32::Foundation::{HLOCAL, LocalFree};
use windows::Win32::Security::Cryptography::{
    CRYPT_INTEGER_BLOB, CRYPTPROTECT_UI_FORBIDDEN, CryptProtectData, CryptUnprotectData,
};
use windows::core::PCWSTR;

use crate::error::{LauncherError, LauncherResult};

pub fn encrypt_password(plain_text: &str) -> LauncherResult<String> {
    if plain_text.is_empty() {
        return Ok(String::new());
    }
    let protected = protect(plain_text.as_bytes())?;
    Ok(STANDARD.encode(protected))
}

pub fn decrypt_password(encrypted_text: &str) -> LauncherResult<String> {
    if encrypted_text.is_empty() {
        return Ok(String::new());
    }
    let encrypted = STANDARD
        .decode(encrypted_text)
        .map_err(|error| LauncherError::message(format!("Invalid encrypted password: {error}")))?;
    let plain = unprotect(&encrypted)?;
    String::from_utf8(plain)
        .map_err(|error| LauncherError::message(format!("Password is not valid UTF-8: {error}")))
}

fn protect(data: &[u8]) -> LauncherResult<Vec<u8>> {
    let input = CRYPT_INTEGER_BLOB {
        cbData: data.len() as u32,
        pbData: data.as_ptr().cast_mut(),
    };
    let mut output = CRYPT_INTEGER_BLOB::default();

    // DPAPI allocates the output buffer with LocalAlloc, so ownership must be
    // returned with LocalFree after the bytes have been copied into Rust memory.
    unsafe {
        CryptProtectData(
            &input,
            PCWSTR::null(),
            None,
            None,
            None,
            CRYPTPROTECT_UI_FORBIDDEN,
            &mut output,
        )
        .map_err(|error| {
            LauncherError::message(format!("Failed to encrypt SQL password: {error}"))
        })?;
        copy_and_free(output)
    }
}

fn unprotect(data: &[u8]) -> LauncherResult<Vec<u8>> {
    let input = CRYPT_INTEGER_BLOB {
        cbData: data.len() as u32,
        pbData: data.as_ptr().cast_mut(),
    };
    let mut output = CRYPT_INTEGER_BLOB::default();

    unsafe {
        CryptUnprotectData(
            &input,
            None,
            None,
            None,
            None,
            CRYPTPROTECT_UI_FORBIDDEN,
            &mut output,
        )
        .map_err(|error| {
            LauncherError::message(format!("Failed to decrypt SQL password: {error}"))
        })?;
        copy_and_free(output)
    }
}

unsafe fn copy_and_free(blob: CRYPT_INTEGER_BLOB) -> LauncherResult<Vec<u8>> {
    if blob.pbData.is_null() && blob.cbData != 0 {
        return Err(LauncherError::message(
            "Windows DPAPI returned an invalid buffer.",
        ));
    }

    let bytes = if blob.cbData == 0 {
        Vec::new()
    } else {
        // SAFETY: DPAPI returned a buffer containing exactly cbData initialized bytes.
        unsafe { slice::from_raw_parts(blob.pbData, blob.cbData as usize).to_vec() }
    };
    if !blob.pbData.is_null() {
        // SAFETY: DPAPI documents that its output buffer must be released by LocalFree.
        unsafe {
            let _ = LocalFree(Some(HLOCAL(blob.pbData.cast())));
        }
    }
    Ok(bytes)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dpapi_round_trip_preserves_unicode_password() {
        let encrypted = encrypt_password("acore-žluťoučký-🔒").expect("encryption should succeed");
        assert_ne!(encrypted, "acore-žluťoučký-🔒");
        assert_eq!(
            decrypt_password(&encrypted).expect("decryption should succeed"),
            "acore-žluťoučký-🔒"
        );
    }

    #[test]
    fn empty_password_has_no_dpapi_payload() {
        assert_eq!(encrypt_password("").expect("empty encryption"), "");
        assert_eq!(decrypt_password("").expect("empty decryption"), "");
    }
}
