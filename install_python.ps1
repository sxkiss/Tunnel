# ==============================================================================
# Python Environment Auto-Installer for Windows (PowerShell)
#
# This script must be run with administrative privileges to install Python.
# To run: Right-click -> Run with PowerShell
# ==============================================================================

# --- Configuration ---
$pythonVersion = "3.11.3"
$installerUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-amd64.exe"
$installerFilename = "python-$pythonVersion-amd64.exe"
$scriptDir = $PSScriptRoot

# --- Check for Administrator Privileges ---
Write-Host "Checking for administrator privileges..."
try {
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Administrator privileges are required."
    }
    Write-Host "Administrator privileges confirmed."
}
catch {
    Write-Host ""
    Write-Host "----------------------------------------------------" -ForegroundColor Red
    Write-Host "ERROR: Please run this script as an administrator." -ForegroundColor Red
    Write-Host "(Right-click on the file > Run with PowerShell)" -ForegroundColor Yellow
    Write-Host "----------------------------------------------------" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# --- Check if Python is Already Installed ---
Write-Host ""
Write-Host "Checking for existing Python installation..."
$pythonPath = Get-Command python -ErrorAction SilentlyContinue
if ($pythonPath) {
    Write-Host "Python is already installed at: $($pythonPath.Source)" -ForegroundColor Green
    Read-Host "Press Enter to exit"
    exit 0
}

Write-Host "Python not found. Starting automatic installation..."

# --- Download Python Installer ---
$installerFullPath = Join-Path -Path $scriptDir -ChildPath $installerFilename
Write-Host ""
if (Test-Path $installerFullPath) {
    Write-Host ">>> [1/3] Python installer found, skipping download." -ForegroundColor Cyan
}
else {
    Write-Host ">>> [1/3] Downloading Python $pythonVersion installer..." -ForegroundColor Cyan
    try {
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerFullPath -UseBasicParsing
    }
    catch {
        Write-Host ""
        Write-Host "----------------------------------------------------" -ForegroundColor Red
        Write-Host "ERROR: Failed to download the Python installer." -ForegroundColor Red
        Write-Host "Please download it manually from: $installerUrl" -ForegroundColor Yellow
        Write-Host "And place it in the same directory as this script." -ForegroundColor Yellow
        Write-Host "Then, run this script again." -ForegroundColor Yellow
        Write-Host "----------------------------------------------------" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# --- Silent Install ---
Write-Host ""
Write-Host ">>> [2/3] Silently installing Python..." -ForegroundColor Cyan
Write-Host "This may take a few moments. Please wait..."
$arguments = "/quiet InstallAllUsers=1 PrependPath=1"
$process = Start-Process -FilePath $installerFullPath -ArgumentList $arguments -Wait -PassThru
if ($process.ExitCode -ne 0) {
    Write-Host "An error occurred during installation. Exit code: $($process.ExitCode)" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# --- Cleanup ---
Write-Host ""
Write-Host ">>> [3/3] Installation complete. Cleaning up installer..." -ForegroundColor Cyan
Remove-Item -Path $installerFullPath -Force

Write-Host ""
Write-Host "----------------------------------------------------" -ForegroundColor Green
Write-Host "Python $pythonVersion has been successfully installed!" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANT:" -ForegroundColor Yellow
Write-Host "Please close this window and open a NEW terminal" -ForegroundColor Yellow
Write-Host "before running the build script to ensure the new" -ForegroundColor Yellow
Write-Host "system PATH takes effect." -ForegroundColor Yellow
Write-Host "----------------------------------------------------" -ForegroundColor Green
Read-Host "Press Enter to exit"