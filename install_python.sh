#!/bin/bash
# -----------------------------------------------------------------------------
# Python Environment Auto-Installer Helper for Linux & macOS
#
# This script detects the OS and provides commands to install Python 3.
# It should be run with sudo privileges to install software.
# -----------------------------------------------------------------------------

# --- Check for root/sudo privileges ---
if [ "$EUID" -ne 0 ]; then
  echo "----------------------------------------------------"
  echo "ERROR: Please run this script with sudo."
  echo "Usage: sudo ./install_python.sh"
  echo "----------------------------------------------------"
  exit 1
fi

# --- Check if Python is already installed ---
if command -v python3 &> /dev/null; then
    echo "----------------------------------------------------"
    echo "Python 3 is already installed."
    echo "Version: $(python3 -V)"
    echo "No action needed."
    echo "----------------------------------------------------"
    exit 0
fi

# --- Provide OS-specific installation instructions ---
echo "----------------------------------------------------"
echo "Python 3 is not installed. Attempting to install..."
echo ""

if [[ "$(uname)" == "Linux" ]]; then
    # --- Linux ---
    if command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        echo "[ Detected Debian/Ubuntu ]"
        echo "Running: apt-get update && apt-get install -y python3 python3-venv python3-pip"
        apt-get update && apt-get install -y python3 python3-venv python3-pip
    elif command -v dnf &> /dev/null; then
        # Fedora/CentOS
        echo "[ Detected Fedora/CentOS ]"
        echo "Running: dnf install -y python3 python3-pip"
        dnf install -y python3 python3-pip
    elif command -v pacman &> /dev/null; then
        # Arch Linux
        echo "[ Detected Arch Linux ]"
        echo "Running: pacman -Syu --noconfirm python python-pip"
        pacman -Syu --noconfirm python python-pip
    else
        echo "ERROR: Could not detect a known package manager (apt, dnf, pacman)."
        echo "Please install Python 3, pip, and venv manually."
        exit 1
    fi
elif [[ "$(uname)" == "Darwin" ]]; then
    # --- macOS ---
    echo "[ Detected macOS ]"
    if ! command -v brew &> /dev/null; then
        echo "ERROR: Homebrew is not installed."
        echo "Please install Homebrew first by visiting https://brew.sh/"
        exit 1
    fi
    echo "Running: brew install python"
    brew install python
else
    echo "ERROR: Unsupported operating system."
    exit 1
fi

# --- Verify installation ---
if command -v python3 &> /dev/null; then
    echo ""
    echo "----------------------------------------------------"
    echo "Python 3 has been successfully installed!"
    echo "Version: $(python3 -V)"
    echo "----------------------------------------------------"
else
    echo ""
    echo "----------------------------------------------------"
    echo "ERROR: Installation failed. Please check the output above."
    echo "----------------------------------------------------"
    exit 1
fi