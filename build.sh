#!/bin/bash
# -----------------------------------------------------------------------------
# All-in-One Build Script for Linux & macOS
#
# This script automates the entire build process.
# -----------------------------------------------------------------------------

# --- Configuration ---
VENV_DIR="venv"
PYTHON_CMD="python3"
MAIN_SCRIPT="main.py"
APP_NAME="TunnelManager"
REQUIREMENTS_FILE="requirements.txt"

# --- Change to script's directory ---
cd "$(dirname "$0")"

# --- 1. Check for Python ---
echo ">>> [1/6] Checking for Python 3 environment..."
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo ""
    echo "----------------------------------------------------"
    echo "ERROR: Python 3 is not found in your system."
    echo ""
    echo "Please run the installation script with sudo first:"
    echo "  sudo ./install_python.sh"
    echo "----------------------------------------------------"
    exit 1
fi
echo "Python 3 found."

# --- 2. Setup Virtual Environment ---
echo ""
echo ">>> [2/6] Setting up Python virtual environment ('$VENV_DIR')..."
if [ -d "$VENV_DIR" ]; then
    echo "      Found existing virtual environment."
else
    echo "      Creating new virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "      ERROR: Failed to create virtual environment."
        exit 1
    fi
fi

# --- 3. Install/Update Build Tools ---
echo ""
echo ">>> [3/6] Installing/updating build tools (pip, wheel)..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip wheel
if [ $? -ne 0 ]; then
    echo "      ERROR: Failed to upgrade pip."
    exit 1
fi

# --- 4. Install PyInstaller ---
echo ""
echo ">>> [4/6] Installing PyInstaller..."
"$VENV_DIR/bin/pip" install --upgrade pyinstaller
if [ $? -ne 0 ]; then
    echo "      ERROR: Failed to install PyInstaller."
    exit 1
fi

# --- 5. Install Dependencies ---
echo ""
echo ">>> [5/6] Installing project dependencies..."
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "      Found '$REQUIREMENTS_FILE', installing dependencies..."
    "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS_FILE"
    if [ $? -ne 0 ]; then
        echo "      ERROR: Failed to install dependencies from '$REQUIREMENTS_FILE'."
        exit 1
    fi
else
    echo "      '$REQUIREMENTS_FILE' not found, skipping."
fi

# --- 6. Run PyInstaller ---
echo ""
echo ">>> [6/6] Bundling the application with PyInstaller..."
"$VENV_DIR/bin/pyinstaller" \
    --name "$APP_NAME" \
    --onefile \
    --windowed \
    --clean \
    "$MAIN_SCRIPT"

if [ $? -ne 0 ]; then
    echo ""
    echo "----------------------------------------------------"
    echo "ERROR: PyInstaller failed to bundle the application!"
    echo "Please check the output above for errors."
    echo "----------------------------------------------------"
    exit 1
fi

# --- Done ---
echo ""
echo "----------------------------------------------------"
echo "Build successful!"
echo "The executable is located in the 'dist' directory."
echo "----------------------------------------------------"