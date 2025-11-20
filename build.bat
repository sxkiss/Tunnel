@echo off
setlocal

rem ==============================================================================
rem All-in-One Build Script for Windows (for CMD)
rem
rem This script automates the entire build process.
rem ==============================================================================

rem --- Configuration ---
set VENV_DIR=venv
set PYTHON_CMD=python
set MAIN_SCRIPT=main.py
set APP_NAME=TunnelManager
set REQUIREMENTS_FILE=requirements.txt

rem --- Change to script's directory ---
cd /d "%~dp0"

rem --- 1. Check for Python ---
echo >>> [1/6] Checking for Python environment...
where %PYTHON_CMD% >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ----------------------------------------------------
    echo ERROR: Python is not found in your system PATH.
    echo.
    echo Please run 'install_python.bat' as an administrator
    echo first to set up the required environment.
    echo ----------------------------------------------------
    pause
    exit /b 1
)
echo Python found.

rem --- 2. Setup Virtual Environment ---
echo.
echo >>> [2/6] Setting up Python virtual environment ('%VENV_DIR%')...
if exist "%VENV_DIR%" (
    echo      Found existing virtual environment.
) else (
    echo      Creating new virtual environment...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo      ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

rem --- 3. Install/Update Build Tools ---
echo.
echo >>> [3/6] Installing/updating build tools (pip, wheel)...
call "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip wheel
if %errorlevel% neq 0 (
    echo      ERROR: Failed to upgrade pip.
    pause
    exit /b 1
)

rem --- 4. Install PyInstaller ---
echo.
echo >>> [4/6] Installing PyInstaller...
call "%VENV_DIR%\Scripts\pip.exe" install --upgrade pyinstaller
if %errorlevel% neq 0 (
    echo      ERROR: Failed to install PyInstaller.
    pause
    exit /b 1
)

rem --- 5. Install Dependencies ---
echo.
echo >>> [5/6] Installing project dependencies...
if exist "%REQUIREMENTS_FILE%" (
    echo      Found %REQUIREMENTS_FILE%, installing dependencies...
    call "%VENV_DIR%\Scripts\pip.exe" install -r "%REQUIREMENTS_FILE%"
    if %errorlevel% neq 0 (
        echo      ERROR: Failed to install dependencies from %REQUIREMENTS_FILE%.
        pause
        exit /b 1
    )
) else (
    echo      '%REQUIREMENTS_FILE%' not found, skipping.
)

rem --- 6. Run PyInstaller ---
echo.
echo >>> [6/6] Bundling the application with PyInstaller...
call "%VENV_DIR%\Scripts\pyinstaller.exe" ^
    --name "%APP_NAME%" ^
    --onefile ^
    --windowed ^
    --clean ^
    "%MAIN_SCRIPT%"

if %errorlevel% neq 0 (
    echo.
    echo ----------------------------------------------------
    echo ERROR: PyInstaller failed to bundle the application!
    echo Please check the output above for errors.
    echo ----------------------------------------------------
    pause
    exit /b 1
)

rem --- Done ---
echo.
echo ----------------------------------------------------
echo Build successful!
echo The executable "%APP_NAME%.exe" is located in the 'dist' directory.
echo ----------------------------------------------------
pause
endlocal