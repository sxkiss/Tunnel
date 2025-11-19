@echo off
setlocal

rem ----------------------------------------------------
rem Windows Build Script for TunnelManager
rem ----------------------------------------------------
rem
rem 使用方法:
rem 1. 确保此脚本与你的主 Python 文件在同一个目录下。
rem 2. 将下面的 "your_main_script.py" 修改为你的主程序文件名。
rem 3. (可选) 如果你有 requirements.txt 文件，此脚本会自动安装依赖。
rem 4. 双击运行此 build.bat 文件。
rem
rem 注意:
rem - 必须在 Windows 系统上运行此脚本以构建 .exe 文件。
rem - 脚本会自动创建 Python 虚拟环境 (venv) 以确保构建环境的纯净。

rem --- 配置 ---
set VENV_DIR=venv
set PYTHON_CMD=python
rem ！！！【请修改这里】将 "your_main_script.py" 替换为你的主程序文件名 ！！！
set MAIN_SCRIPT=main.py
set APP_NAME=TunnelManager
set REQUIREMENTS_FILE=requirements.txt

rem 确保我们位于脚本所在的目录
cd /d "%~dp0"

rem --- 检查主脚本文件是否存在 ---
if not exist "%MAIN_SCRIPT%" (
    echo ----------------------------------------------------
    echo 错误: 主脚本文件 "%MAIN_SCRIPT%" 不存在!
    echo.
    echo 请在脚本中修改 "MAIN_SCRIPT" 变量，
    echo 使其指向正确的 Python 主程序文件。
    echo ----------------------------------------------------
    pause
    exit /b 1
)

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
echo.
echo >>> [1/5] 正在检查并设置 Python 虚拟环境 ('%VENV_DIR%')...
if not exist "%VENV_DIR%" (
    echo      未检测到虚拟环境，正在创建...
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo      错误: 创建虚拟环境失败。
        pause
        exit /b 1
    )
) else (
    echo      检测到已存在的虚拟环境，将直接使用。
)
call "%VENV_DIR%\Scripts\activate.bat"

rem --- 安装/更新构建工具 ---
echo.
echo >>> [2/5] 正在虚拟环境中安装/更新构建工具 (pip, wheel, pyinstaller)...
pip install --upgrade pip wheel
pip install --upgrade pyinstaller
if %errorlevel% neq 0 (
    echo      错误: 安装 PyInstaller 失败。
    pause
    exit /b 1
)

rem --- 安装项目依赖 ---
echo.
echo >>> [3/5] 正在安装项目依赖...
if exist "%REQUIREMENTS_FILE%" (
    echo      发现 %REQUIREMENTS_FILE%，正在安装依赖...
    pip install -r "%REQUIREMENTS_FILE%"
    if %errorlevel% neq 0 (
        echo      错误: 从 %REQUIREMENTS_FILE% 安装依赖失败。
        pause
        exit /b 1
    )
) else (
    echo      未发现 %REQUIREMENTS_FILE%，跳过此步骤。
)


rem --- 执行打包 ---
echo.
echo >>> [4/5] 正在使用 PyInstaller 打包应用 "%APP_NAME%"...
pyinstaller ^
    --name "%APP_NAME%" ^
    --onefile ^
    --windowed ^
    --clean ^
    "%MAIN_SCRIPT%"

rem 如果打包失败，给出提示
if %errorlevel% neq 0 (
    echo.
    echo ----------------------------------------------------
    echo 错误: PyInstaller 打包失败！
    echo 请检查上面的错误信息。
    echo 常见的失败原因包括:
    echo  - Python 脚本自身存在语法错误。
    echo  - 缺少必要的依赖库 (请确保已创建 requirements.txt)。
    echo  - 脚本中使用了 PyInstaller 无法找到的隐藏导入或数据文件。
    echo ----------------------------------------------------
    deactivate
    pause
    exit /b 1
)

rem --- 完成 ---
echo.
echo >>> [5/5] 打包完成！
echo ----------------------------------------------------
echo.
echo 可执行文件 "%APP_NAME%.exe" 已生成在 'dist' 目录中。
echo.
echo ----------------------------------------------------

rem 退出虚拟环境 (在批处理脚本结束时会自动处理)
deactivate
pause
endlocal