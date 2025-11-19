#!/bin/bash
# ==============================================================================
# Python 环境自动化安装脚本 (适用于 Debian/Ubuntu)
# ==============================================================================
#
# 功能:
#   - 检查 Python 版本是否 >= 3.11.3
#   - 如果不满足，则自动下载 Python 3.11.3 源码并进行编译安装。
#   - 自动安装编译所需的依赖包 (build-essential, ssl, etc.)。
#   - 配置 pip 使用国内镜像源。
#
# 使用方法:
#   在终端中运行: sudo ./setup_environment.sh
#
# 注意:
#   - 此脚本需要以 root/sudo 权限运行，因为它需要使用 apt 安装系统依赖。
#   - 仅为 Debian/Ubuntu 及其衍生版设计。
#   - 会将 Python 3.11.3 安装到 /usr/local/bin，可能会覆盖旧版本。
#
# ==============================================================================

set -e

MIN_PYTHON_VERSION="3.11.3"
PYTHON_VERSION_TUPLE=$(echo "$MIN_PYTHON_VERSION" | awk -F. '{printf "(\"%s\", \"%s\", \"%s\")", $1, $2, $3}')

# 检查 Python 版本
if python3 -c "import sys; assert sys.version_info >= $PYTHON_VERSION_TUPLE" &> /dev/null; then
    echo "Python 版本满足要求 (>= $MIN_PYTHON_VERSION)。无需安装。"
    exit 0
fi

echo "Python 环境不满足要求，即将开始自动化安装..."

# 1. 更新包列表并安装编译依赖
echo ">>> [1/4] 正在安装编译 Python 所需的系统依赖..."
apt-get update
apt-get install -y \
    build-essential \
    zlib1g-dev \
    libncurses5-dev \
    libgdbm-dev \
    libnss3-dev \
    libssl-dev \
    libreadline-dev \
    libffi-dev \
    libsqlite3-dev \
    wget \
    curl \
    xz-utils \
    tk-dev \
    libxml2-dev \
    libxmlsec1-dev \
    liblzma-dev

# 2. 下载并解压 Python 源码
PYTHON_MAJOR_VERSION=$(echo "$MIN_PYTHON_VERSION" | cut -d. -f1,2)
PYTHON_TARBALL="Python-$MIN_PYTHON_VERSION.tgz"
PYTHON_SRC_DIR="Python-$MIN_PYTHON_VERSION"

echo ">>> [2/4] 正在下载 Python $MIN_PYTHON_VERSION 源码..."
if [ ! -f "$PYTHON_TARBALL" ]; then
    wget "https://www.python.org/ftp/python/$MIN_PYTHON_VERSION/$PYTHON_TARBALL"
fi

echo "正在解压..."
tar -xzf "$PYTHON_TARBALL"

# 3. 编译并安装 Python
echo ">>> [3/4] 正在编译并安装 Python，这可能需要几分钟时间..."
cd "$PYTHON_SRC_DIR"
./configure --enable-optimizations --enable-loadable-sqlite-extensions
make -j "$(nproc)"
make altinstall # 使用 altinstall 避免覆盖系统默认的 python3

# 4. 配置 pip 并验证
echo ">>> [4/4] 正在配置 pip 并验证安装..."
cd ..
python$PYTHON_MAJOR_VERSION -m pip install --upgrade pip
python$PYTHON_MAJOR_VERSION -m pip config set global.index-url https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple

echo "----------------------------------------------------"
echo "Python $MIN_PYTHON_VERSION 安装成功！"
echo "请使用 'python$PYTHON_MAJOR_VERSION' 来调用新版本。"
python$PYTHON_MAJOR_VERSION --version
echo "----------------------------------------------------"
