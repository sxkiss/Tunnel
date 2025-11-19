@echo off
rem ----------------------------------------------------
rem Windows Build Script for TunnelManager
rem ----------------------------------------------------
rem
rem 使用方法:
rem 1. 双击运行此 build.bat 文件。
rem
rem 注意:
rem - 必须在 Windows 系统上运行此脚本以构建 .exe 文件。
rem - 脚本会自动创建 Python 虚拟环境 (venv) 并安装 PyInstaller，
rem   以确保构建环境的纯净。

rem --- 配置 ---
set VENV_DIR=venv
set PYTHON_CMD=python
set MAIN_SCRIPT=./1_linux.py
set APP_NAME=TunnelManager

rem 确保我们位于脚本所在的目录
cd /d "%~dp0"

rem --- 检查 Python 环境 ---
where %PYTHON_CMD% >nul 2>nul
if %errorlevel% neq 0 (
    echo ----------------------------------------------------
    echo 错误: 系统中未找到 Python 环境。
    echo.
    echo 您可以运行环境设置脚本来自动安装 Python 3.11.3:
    echo   1. 找到项目中的 setup_environment.bat 文件。
    echo   2. 右键点击它，选择 "以管理员身份运行"。
    echo.
    echo 环境配置完成后，请重新打开一个新的终端窗口
    echo 并再次运行此构建脚本。
    echo ----------------------------------------------------
    pause
    exit /b 1
)

rem --- 虚拟环境设置 ---
echo >>> [1/4] 正在检查并激活 Python 虚拟环境 ('%VENV_DIR%')...
if not exist "%VENV_DIR%" (
    echo 未检测到虚拟环境，正在创建...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo 创建虚拟环境失败。
        pause
        exit /b 1
    )
) else (
    echo 检测到已存在的虚拟环境，将直接使用。
)
call "%VENV_DIR%\Scripts\activate.bat"

rem --- 安装依赖 ---
echo >>> [2/4] 正在虚拟环境中安装/更新 PyInstaller...
pip install --upgrade pip wheel
pip install --upgrade pyinstaller

rem --- 执行打包 ---
echo >>> [3/4] 正在使用 PyInstaller 打包应用...
pyinstaller ^
    --name "%APP_NAME%" ^
    --onefile ^
    --windowed ^
    "%MAIN_SCRIPT%"

rem 如果您有图标文件，可以取消下面的注释并修改路径
rem --icon="assets/icon.ico"

rem --- 完成 ---
echo >>> [4/4] 打包完成！
echo 可执行文件已生成在 'dist' 目录中。
echo ----------------------------------------------------

rem 退出虚拟环境 (在批处理脚本结束时会自动处理)
deactivate
pause