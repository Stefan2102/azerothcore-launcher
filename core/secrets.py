from __future__ import annotations

import base64
import ctypes
import sys
from ctypes import Structure, byref, cast, create_string_buffer, windll
from ctypes.wintypes import DWORD


# ==========================================
# PASSWORD PROTECTION (WINDOWS DPAPI)
# ==========================================


class SecretError(RuntimeError):
    pass


class _DataBlob(Structure):
    _fields_ = [("cbData", DWORD), ("pbData", ctypes.c_void_p)]


def encrypt_password(plain_text: str) -> str:
    if not plain_text:
        return ""
    if sys.platform != "win32":
        raise SecretError("Password encryption is only supported on Windows.")
    blob = _protect(plain_text.encode("utf-8"))
    return base64.b64encode(blob).decode("ascii")


def decrypt_password(encrypted_text: str) -> str:
    if not encrypted_text:
        return ""
    if sys.platform != "win32":
        raise SecretError("Password decryption is only supported on Windows.")
    blob = base64.b64decode(encrypted_text.encode("ascii"))
    return _unprotect(blob).decode("utf-8")


def _protect(data: bytes) -> bytes:
    input_blob = _DataBlob(len(data), cast(create_string_buffer(data), ctypes.c_void_p))
    output_blob = _DataBlob()
    if not windll.crypt32.CryptProtectData(byref(input_blob), None, None, None, None, 0, byref(output_blob)):
        raise SecretError("Failed to encrypt password.")
    buffer = ctypes.string_at(output_blob.pbData, output_blob.cbData)
    windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    windll.kernel32.LocalFree(output_blob.pbData)
    return buffer


def _unprotect(data: bytes) -> bytes:
    input_blob = _DataBlob(len(data), cast(create_string_buffer(data), ctypes.c_void_p))
    output_blob = _DataBlob()
    if not windll.crypt32.CryptUnprotectData(byref(input_blob), None, None, None, None, 0, byref(output_blob)):
        raise SecretError("Failed to decrypt password.")
    buffer = ctypes.string_at(output_blob.pbData, output_blob.cbData)
    windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    windll.kernel32.LocalFree(output_blob.pbData)
    return buffer
