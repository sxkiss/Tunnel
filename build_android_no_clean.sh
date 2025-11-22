#!/bin/bash
set -e # 如果任何命令失败，立即退出
set -o pipefail # 确保管道中的命令失败时，脚本也会退出

VENV_DIR=".venv_android"

echo "INFO: 准备开始安卓应用打包（保留所有缓存）..."

# 1. 创建并准备虚拟环境 (如果不存在)
if [ ! -d "$VENV_DIR" ]; then
    echo "INFO: 正在创建 Python 虚拟环境..."
    python3 -m venv "$VENV_DIR"
fi

# 2. 激活虚拟环境
echo "INFO: 正在激活虚拟环境..."
source "$VENV_DIR/bin/activate"

# 3. 在虚拟环境中安装/更新核心依赖
echo "INFO: 正在虚拟环境中安装/更新核心依赖 (setuptools, cython, buildozer)..."
pip install -U setuptools cython buildozer

# 4. 清理并配置 Git (解决 SSL 后端错误和网络超时问题)
echo "INFO: 正在清理潜在的错误 Git SSL 后端配置..."
git config --global --unset http.sslBackend || true

echo "INFO: 配置 Git 以适应慢速网络，防止下载超时..."
git config --global http.lowSpeedTime 999999
git config --global http.lowSpeedLimit 0

# 5. 不清理任何缓存，保留所有下载的依赖
echo "INFO: 跳过缓存清理，保留所有已下载的依赖..."

# 6. 运行 buildozer 完成构建
echo "INFO: 现在正式启动 Buildozer 打包进程（保留缓存）..."
buildozer -v android debug 2>&1 | tee build.log

# 7. 完成提示
echo "成功: 打包完成！"
echo "APK 文件已生成在 'bin' 目录下。"

# 8. 退出虚拟环境
deactivate