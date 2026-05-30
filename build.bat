@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv" (
    py -3.11 -m venv ".venv" || python -m venv ".venv"
    if errorlevel 1 goto fail
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto fail

echo.
echo Using Python:
python --version
echo.

python -m pip install --upgrade pip
if errorlevel 1 goto fail

python -m pip install -r requirements.txt
if errorlevel 1 goto fail

python -m pip install pyinstaller
if errorlevel 1 goto fail

pyinstaller --noconfirm --clean "AzerothCore Launcher.spec"

if errorlevel 1 goto fail

echo.
echo Build complete: dist\AzerothCore Launcher.exe
echo.
pause
endlocal
exit /b 0

:fail
echo.
echo Build failed. Review the error output above.
echo.
pause
endlocal
exit /b 1
