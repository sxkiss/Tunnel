@echo off
setlocal

rem ==============================================================================
rem Python Environment Auto-Installer for Windows (for CMD)
rem
rem This script must be run with administrative privileges to install Python.
rem ==============================================================================

rem --- Configuration ---
set PYTHON_VERSION=3.11.3
set INSTALLER_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-amd64.exe
set INSTALLER_FILENAME=python-%PYTHON_VERSION%-amd64.exe

rem --- Check for Administrator Privileges ---
echo Checking for administrator privileges...
openfiles >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ----------------------------------------------------
    echo ERROR: Please run this script as an administrator.
    echo (Right-click ^> Run as administrator)
    echo ----------------------------------------------------
    pause
    exit /b 1
)
echo Administrator privileges confirmed.

rem --- Check if Python is Already Installed ---
echo.
echo Checking for existing Python installation...
where python >nul 2>&1
if %errorlevel% equ 0 (
    echo Python is already installed. No action needed.
    pause
    exit /b 0
)

echo Python not found. Starting automatic installation...

rem --- Download Python Installer ---
echo.
if exist "%INSTALLER_FILENAME%" (
    echo >>> [1/3] Python installer found, skipping download.
) else (
    echo >>> [1/3] Downloading Python %PYTHON_VERSION% installer...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '%INSTALLER_URL%' -OutFile '%INSTALLER_FILENAME%'"
    if %errorlevel% neq 0 (
        echo.
        echo ----------------------------------------------------
        echo ERROR: Failed to download the Python installer.
        echo Please download it manually from: %INSTALLER_URL%
        echo And place it in the same directory as this script.
        echo Then, run this script again.
        echo ----------------------------------------------------
        pause
        exit /b 1
    )
)

rem --- Silent Install ---
echo.
echo >>> [2/3] Silently installing Python...
echo This may take a few moments. Please wait...
start /wait %INSTALLER_FILENAME% /quiet InstallAllUsers=1 PrependPath=1
if %errorlevel% neq 0 (
    echo An error occurred during installation.
    pause
    exit /b 1
)

rem --- Cleanup ---
echo.
echo >>> [3/3] Installation complete. Cleaning up installer...
del %INSTALLER_FILENAME%

echo.
echo ----------------------------------------------------
echo Python %PYTHON_VERSION% has been successfully installed!
echo.
echo IMPORTANT:
echo Please close this window and open a NEW terminal
echo before running the build script to ensure the new
echo system PATH takes effect.
echo ----------------------------------------------------
pause
exit /b 0