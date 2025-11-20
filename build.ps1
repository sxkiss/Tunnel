# ==============================================================================
# All-in-One Build Script for Windows (PowerShell)
#
# This script automates the entire build process.
# To run: Open PowerShell, navigate to this directory, and run '.\build.ps1'
# ==============================================================================

# --- Configuration ---
$venvDir = "venv"
$pythonCmd = "python"
$mainScript = "main.py"
$appName = "TunnelManager"
$requirementsFile = "requirements.txt"
$scriptDir = $PSScriptRoot

# --- Function to run commands and handle errors ---
function Invoke-CommandWithErrorHandling {
    param(
        [string]$command,
        [string[]]$arguments
    )
    Write-Host ""
    Write-Host "--- Running command: $command $($arguments -join ' ') ---" -ForegroundColor Yellow
    try {
        $process = Start-Process -FilePath $command -ArgumentList $arguments -Wait -PassThru -NoNewWindow
        if ($process.ExitCode -ne 0) {
            throw "Command failed with exit code $($process.ExitCode)."
        }
    }
    catch {
        Write-Host ""
        Write-Host "----------------------------------------------------" -ForegroundColor Red
        Write-Host "ERROR: An error occurred while executing the command." -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        Write-Host "----------------------------------------------------" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# --- 1. Check for Python ---
Write-Host ">>> [1/6] Checking for Python environment..." -ForegroundColor Cyan
$pythonPath = Get-Command $pythonCmd -ErrorAction SilentlyContinue
if (-not $pythonPath) {
    Write-Host ""
    Write-Host "----------------------------------------------------" -ForegroundColor Red
    Write-Host "ERROR: Python is not found in your system PATH." -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run 'install_python.ps1' as an administrator" -ForegroundColor Yellow
    Write-Host "first to set up the required environment." -ForegroundColor Yellow
    Write-Host "----------------------------------------------------" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "Python found at: $($pythonPath.Source)"

# --- 2. Setup Virtual Environment ---
$venvFullPath = Join-Path -Path $scriptDir -ChildPath $venvDir
Write-Host ""
Write-Host ">>> [2/6] Setting up Python virtual environment ('$venvDir')..." -ForegroundColor Cyan
if (Test-Path $venvFullPath) {
    Write-Host "      Found existing virtual environment."
}
else {
    Write-Host "      Creating new virtual environment..."
    Invoke-CommandWithErrorHandling -command $pythonCmd -arguments "-m", "venv", $venvDir
}

# --- Define paths for venv executables ---
$venvPython = Join-Path -Path $venvFullPath -ChildPath "Scripts\python.exe"
$venvPip = Join-Path -Path $venvFullPath -ChildPath "Scripts\pip.exe"
$venvPyInstaller = Join-Path -Path $venvFullPath -ChildPath "Scripts\pyinstaller.exe"

# --- 3. Install/Update Build Tools ---
Write-Host ""
Write-Host ">>> [3/6] Installing/updating build tools (pip, wheel)..." -ForegroundColor Cyan
Invoke-CommandWithErrorHandling -command $venvPython -arguments "-m", "pip", "install", "--upgrade", "pip", "wheel"

# --- 4. Install PyInstaller ---
Write-Host ""
Write-Host ">>> [4/6] Installing PyInstaller..." -ForegroundColor Cyan
Invoke-CommandWithErrorHandling -command $venvPip -arguments "install", "--upgrade", "pyinstaller"

# --- 5. Install Dependencies ---
$requirementsFullPath = Join-Path -Path $scriptDir -ChildPath $requirementsFile
Write-Host ""
Write-Host ">>> [5/6] Installing project dependencies..." -ForegroundColor Cyan
if (Test-Path $requirementsFullPath) {
    Write-Host "      Found '$requirementsFile', installing dependencies..."
    Invoke-CommandWithErrorHandling -command $venvPip -arguments "install", "-r", $requirementsFile
}
else {
    Write-Host "      '$requirementsFile' not found, skipping."
}

# --- 6. Run PyInstaller ---
Write-Host ""
Write-Host ">>> [6/6] Bundling the application with PyInstaller..." -ForegroundColor Cyan
$pyinstallerArgs = "--name", "`"$appName`"", "--onefile", "--windowed", "--clean", $mainScript
Invoke-CommandWithErrorHandling -command $venvPyInstaller -arguments $pyinstallerArgs

# --- Done ---
Write-Host ""
Write-Host "----------------------------------------------------" -ForegroundColor Green
Write-Host "Build successful!" -ForegroundColor Green
Write-Host "The executable '$appName.exe' is located in the 'dist' directory." -ForegroundColor Green
Write-Host "----------------------------------------------------" -ForegroundColor Green
Read-Host "Press Enter to finish"