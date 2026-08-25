@echo off
setlocal EnableExtensions

title AzerothCore Launcher - Release Build
cls
echo === AzerothCore Launcher - Release Build ===
echo.

cd /d "%~dp0"
if errorlevel 1 (
    set "BUILD_EXIT=1"
    goto fail
)

echo [1/4] Checking required build tools...
echo.
where node >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Node.js was not found on PATH. Install Node.js 22.12 or newer.
    set "BUILD_EXIT=1"
    goto fail
)

where npm >nul 2>nul
if errorlevel 1 (
    echo [ERROR] npm was not found on PATH. Reinstall Node.js with npm enabled.
    set "BUILD_EXIT=1"
    goto fail
)

where cargo >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Cargo was not found on PATH. Install the Rust MSVC toolchain.
    set "BUILD_EXIT=1"
    goto fail
)

echo [2/4] Installing locked frontend dependencies...
echo.
call npm ci
if errorlevel 1 (
    set "BUILD_EXIT=%ERRORLEVEL%"
    goto fail
)

echo.
echo [3/4] Building the optimized Tauri application...
echo.
call npm run tauri build -- --no-bundle
if errorlevel 1 (
    set "BUILD_EXIT=%ERRORLEVEL%"
    goto fail
)

echo.
echo [4/4] Packaging the raw executable...
echo.
if not exist "src-tauri\target\release\azerothcore-launcher.exe" (
    echo [ERROR] Expected release executable was not created.
    set "BUILD_EXIT=1"
    goto fail
)

if not exist "dist" mkdir "dist"
if errorlevel 1 (
    set "BUILD_EXIT=%ERRORLEVEL%"
    goto fail
)

copy /y "src-tauri\target\release\azerothcore-launcher.exe" "dist\AzerothCore Launcher.exe" >nul
if errorlevel 1 (
    set "BUILD_EXIT=%ERRORLEVEL%"
    goto fail
)

echo.
echo [SUCCESS] Build complete: dist\AzerothCore Launcher.exe
echo.
pause
endlocal
exit /b 0

:fail
if not defined BUILD_EXIT set "BUILD_EXIT=1"
echo.
echo [FAILED] Build exited with code %BUILD_EXIT%. Review the error output above.
echo.
pause
endlocal & exit /b %BUILD_EXIT%
