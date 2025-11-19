#!/bin/bash
# ----------------------------------------------------
# Linux & macOS Build Script for TunnelManager
# ----------------------------------------------------
#
# 使用方法:
# 1. 打开终端
# 2. 赋予脚本执行权限: chmod +x build.sh
# 3. 运行脚本: ./build.sh
#
# 注意:
# - 必须在目标操作系统上运行此脚本。
#   (例如，在 macOS 上运行以构建 .app 应用)
# - 脚本会自动创建 Python 虚拟环境 (venv) 并安装 PyInstaller，
#   以确保构建环境的纯净。

# --- 配置 ---
VENV_DIR="venv"
PYTHON_CMD="python3.11" # 优先使用新安装的版本
FALLBACK_PYTHON_CMD="python3"
MAIN_SCRIPT="./1_linux.py"
APP_NAME="TunnelManager"

# 确保我们位于脚本所在的目录
cd "$(dirname "$0")"

# --- 检查 Python 环境 ---
# 优先检查新版本，如果不存在则回退到通用的 python3
if ! command -v $PYTHON_CMD &> /dev/null; then
    PYTHON_CMD=$FALLBACK_PYTHON_CMD
fi

if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "----------------------------------------------------"
    echo "错误: 系统中未找到合适的 Python 3 环境。"
    echo ""
    echo "您可以运行环境设置脚本来自动安装 Python 3.11.3:"
    echo "  1. 赋予权限: chmod +x setup_environment.sh"
    echo "  2. 运行安装: sudo ./setup_environment.sh"
    echo ""
    echo "环境配置完成后，请重新运行此构建脚本。"
    echo "----------------------------------------------------"
    exit 1
fi

# --- 虚拟环境设置 ---
echo ">>> [1/4] 正在检查并激活 Python 虚拟环境 ('$VENV_DIR')..."
echo "为确保构建环境纯净，正在强制重新创建虚拟环境..."
rm -rf "$VENV_DIR"
$PYTHON_CMD -m venv "$VENV_DIR"
if [ $? -ne 0 ]; then
    echo "创建虚拟环境失败。"
    exit 1
fi
# --- 安装依赖 ---
echo ">>> [2/4] 正在虚拟环境中安装/更新 PyInstaller..."
"$VENV_DIR/bin/pip" install --upgrade pip wheel
"$VENV_DIR/bin/pip" install --upgrade pyinstaller

# --- 执行打包 ---
echo ">>> [3/4] 正在使用 PyInstaller 打包应用..."
"$VENV_DIR/bin/pyinstaller" \
    --name "$APP_NAME" \
    --onefile \
    --windowed \
    "$MAIN_SCRIPT"

# 如果您有图标文件，可以取消下面的注释并修改路径
# --icon="assets/icon.icns"

# --- 完成 ---
echo ">>> [4/4] 打包完成！"
echo "可执行文件已生成在 'dist' 目录中。"
echo "----------------------------------------------------"
