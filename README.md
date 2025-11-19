# TunnelManager 使用与打包说明

本项目是一个基于 Python 和 Tkinter 的 Cloudflare Tunnel 客户端管理工具，旨在提供一个简洁的图形界面（GUI）和命令行界面（CLI），用于将远程服务（通过 Cloudflare Tunnel 访问）安全地映射到本地端口。

---

## 一、 软件使用说明

本工具打包后为单个可执行文件，无需安装，开箱即用。它的核心功能是执行 `cloudflared access` 命令，让您可以在本地通过 `localhost:<端口>` 的方式访问一个远程服务。

### 1. 图形界面 (GUI) 模式

直接双击运行 `TunnelManager` 可执行文件即可启动图形界面。

**主要操作:**

*   **隧道列表**: 主窗口会显示所有已配置的连接及其状态（名称、协议、远程主机名、映射的本地端口、运行状态）。
*   **添加隧道**: 点击 `添加隧道` 按钮，在弹出的对话框中填写以下信息：
    *   **连接名称**: 自定义名称，方便识别（例如“公司远程桌面”）。
    *   **远程协议**: 远程服务的协议，如 `rdp`, `tcp`, `ssh` 等。
    *   **远程主机名**: 您要访问的、通过 Cloudflare Tunnel 暴露的服务域名，例如 `rdp.example.com`。
    *   **映射到本地端口**: 您希望在本地用哪个端口来访问这个远程服务，例如 `3389`。配置完成后，您可以通过访问 `localhost:3389` 来连接远程服务。
*   **编辑隧道**: 在列表中选中一个连接，然后点击 `编辑隧道` 按钮进行修改。
*   **删除隧道**: 在列表中选中一个连接，然后点击 `删除隧道` 按钮。如果连接正在运行，程序会先尝试断开它。
*   **启动/停止隧道**: **双击**列表中的任意连接项，即可在其“启动”和“停止”状态之间切换。启动后，本地端口监听开始；停止后，监听结束。

### 2. 命令行 (CLI) 模式

在终端中，使用 `--cli` 参数启动命令行模式。

**基本用法:**
```bash
# 在 Linux/macOS 上
./TunnelManager --cli [命令]

# 在 Windows 上
TunnelManager.exe --cli [命令]
```

**可用命令:**

*   `list` (默认): 显示所有隧道的配置和状态。
    ```bash
    ./TunnelManager --cli list
    ```
*   `add`: 添加一个新的隧道连接。
    ```bash
    # 示例：添加一个名为 "公司RDP" 的连接，它将远程的 rdp.example.com 映射到本地的 3389 端口
    ./TunnelManager --cli add "公司RDP" rdp.example.com 3389 --protocol rdp
    ```
*   `update`: 更新一个已有的隧道连接。
    ```bash
    # 示例：将 "公司RDP" 的远程主机更改为 new.example.com，本地端口更改为 3390
    ./TunnelManager --cli update "公司RDP" --hostname new.example.com --local-port 3390
    ```
*   `delete`: 删除一个隧道连接。
    ```bash
    ./TunnelManager --cli delete "公司RDP"
    ```
*   `start`: 启动一个隧道连接（开始在本地监听）。
    ```bash
    ./TunnelManager --cli start "公司RDP"
    ```
*   `stop`: 停止一个隧道连接（停止本地监听）。
    ```bash
    ./TunnelManager --cli stop "公司RDP"
    ```

---

## 二、 多平台打包说明

本项目提供了一套自动化的脚本，用于在不同操作系统上打包生成独立的可执行文件。

**核心原则**: 打包操作必须在目标操作系统上进行（例如，在 Windows 上打包 `.exe`，在 macOS 上打包 `.app`）。

### 1. 在 Windows 上打包

#### 首次环境准备

如果您的 Windows 系统中没有安装 Python，脚本会自动引导您完成安装：

1.  在项目根目录找到 `setup_environment.bat` 文件。
2.  **右键点击**该文件，选择 **“以管理员身份运行”**。
3.  脚本会自动下载并静默安装 Python，同时配置好系统路径。
4.  安装完成后，**务必关闭并重新打开**一个新的终端窗口。

#### 执行打包

1.  直接**双击运行**项目根目录下的 `build.bat` 文件。
2.  脚本会自动创建虚拟环境、安装依赖并执行打包。

### 2. 在 Linux (Debian/Ubuntu) 上打包

#### 首次环境准备

如果您的系统中没有安装符合要求的 Python 版本：

1.  打开终端，进入项目目录。
2.  给环境安装脚本赋予执行权限：`chmod +x setup_environment.sh`
3.  以 `sudo` 权限运行脚本：`sudo ./setup_environment.sh`
4.  脚本会自动安装编译依赖，并从源码编译安装 Python 3.11.3。

#### 执行打包

1.  打开终端，进入项目目录。
2.  给构建脚本赋予执行权限：`chmod +x build.sh`
3.  运行脚本：`./build.sh`

### 3. 在 macOS 上打包

#### 首次环境准备

macOS 通常不自带 `python3` 命令。推荐使用 [Homebrew](https://brew.sh/) 来安装：
```bash
brew install python
```

#### 执行打包

操作与 Linux 完全相同：
1.  打开终端，进入项目目录。
2.  给构建脚本赋予执行权限：`chmod +x build.sh`
3.  运行脚本：`./build.sh`

### 打包产物

无论在哪种系统上，打包成功后，最终的可执行文件都会生成在项目根目录下的 `dist` 文件夹中。