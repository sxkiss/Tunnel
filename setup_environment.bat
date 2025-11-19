@echo off
rem ==============================================================================
rem Python 环境自动化安装脚本 (适用于 Windows)
rem ==============================================================================
rem
rem 功能:
rem   - 检查 Python 是否已安装。
rem   - 如果未安装，则自动下载 Python 3.11.3 的官方安装包并进行静默安装。
rem   - 安装时会自动添加 Python 到系统 PATH。
rem
rem 使用方法:
rem   右键点击此文件，选择 "以管理员身份运行"。
rem
rem 注意:
rem   - 必须以管理员权限运行，才能成功安装软件并修改系统 PATH。
rem   - 脚本执行完毕后，您可能需要打开一个新的终端窗口才能使 PATH 更改生效。
rem
rem ==============================================================================

setlocal

rem --- 配置 ---
set PYTHON_VERSION=3.11.3
set INSTALLER_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-amd64.exe
set INSTALLER_FILENAME=python-%PYTHON_VERSION%-amd64.exe

rem --- 权限检查 ---
echo 正在检查管理员权限...
openfiles >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ----------------------------------------------------
    echo 错误: 请以管理员身份运行此脚本。
    echo (右键点击 setup_environment.bat -> 以管理员身份运行)
    echo ----------------------------------------------------
    pause
    exit /b 1
)
echo 管理员权限检查通过。

rem --- 检查 Python 是否已安装 ---
echo.
echo 正在检查 Python 环境...
where python >nul 2>nul
if %errorlevel% equ 0 (
    echo Python 已安装。无需重复操作。
    pause
    exit /b 0
)

echo Python 未安装，即将开始自动化安装...

rem --- 下载或检查安装包 ---
echo.
if exist "%INSTALLER_FILENAME%" (
    echo >>> [1/3] 发现已存在的 Python 安装包，跳过下载。
) else (
    echo >>> [1/3] 正在下载 Python %PYTHON_VERSION% 安装包...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '%INSTALLER_URL%' -OutFile '%INSTALLER_FILENAME%'"
    if %errorlevel% neq 0 (
        echo.
        echo ----------------------------------------------------
        echo 错误: Python 安装包自动下载失败。
        echo.
        echo 这可能是由于网络问题或 Python 官网访问限制导致的。
        echo.
        echo 请手动完成以下步骤:
        echo   1. 在浏览器中打开以下链接进行下载:
        echo      %INSTALLER_URL%
        echo.
        echo   2. 下载完成后，将安装包 "%INSTALLER_FILENAME%"
        echo      放置于本脚本所在的目录中。
        echo.
        echo   3. 再次以管理员身份运行本脚本 (setup_environment.bat)。
        echo      脚本会自动跳过下载，直接进行安装。
        echo ----------------------------------------------------
        pause
        exit /b 1
    )
)

rem --- 静默安装 ---
echo.
echo >>> [2/3] 正在静默安装 Python，请稍候...
start /wait %INSTALLER_FILENAME% /quiet InstallAllUsers=1 PrependPath=1
if %errorlevel% neq 0 (
    echo 安装过程中发生错误。
    pause
    exit /b 1
)

rem --- 清理并提示 ---
echo.
echo >>> [3/3] 安装完成，正在清理安装文件...
del %INSTALLER_FILENAME%

echo.
echo ----------------------------------------------------
echo Python %PYTHON_VERSION% 已成功安装！
echo.
echo 重要提示:
echo 请关闭当前终端窗口，然后重新打开一个新的终端
echo 来运行 build.bat，以确保新的 PATH 环境变量生效。
echo ----------------------------------------------------
pause
exit /b 0