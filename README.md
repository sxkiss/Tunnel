# Tunnel Manager - Android 版本

本项目是一个基于 Python 和 Kivy 的 Cloudflare Tunnel 客户端管理工具的 **Android 移动版本**，提供简洁的移动端图形界面，用于将远程服务（通过 Cloudflare Tunnel 访问）安全地映射到本地端口。

> **注意**: 这是 Android 移动版本。如需桌面版本（Windows/Linux/macOS），请查看项目的桌面分支。

---

## 📱 软件功能

本工具的核心功能是执行 `cloudflared access` 命令，让您可以在 Android 设备上通过 `localhost:<端口>` 的方式访问远程服务。

### 主要特性

- ✅ **隧道管理**: 添加、编辑、删除隧道配置
- ✅ **一键启动**: 点击即可启动/停止隧道连接
- ✅ **状态监控**: 实时显示所有隧道的运行状态
- ✅ **多协议支持**: 支持 RDP、SSH、TCP 等多种协议
- ✅ **本地端口映射**: 将远程服务映射到本地端口访问

### 界面操作

1. **隧道列表**: 显示所有已配置的连接及其状态
2. **添加隧道**: 点击添加按钮，填写连接信息：
   - 连接名称（如"公司远程桌面"）
   - 远程协议（如 `rdp`, `tcp`, `ssh`）
   - 远程主机名（如 `rdp.example.com`）
   - 本地端口（如 `3389`）
3. **启动/停止**: 点击隧道项即可切换运行状态
4. **编辑/删除**: 长按隧道项进行编辑或删除操作

---

## 🔧 Android 打包说明

### 系统要求

- **操作系统**: Linux（推荐 Ubuntu 20.04+）
- **Python**: 3.8 或更高版本
- **Java JDK**: OpenJDK 21
- **Android SDK**: API Level 31
- **Android NDK**: r25b

### 快速开始

#### 1. 环境准备

确保已安装必要的依赖：

```bash
# 安装系统依赖
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv \
    openjdk-21-jdk git zip unzip wget curl

# 验证 Java 版本
java -version  # 应显示 OpenJDK 21
```

#### 2. 构建 APK

使用提供的构建脚本（推荐，会保留缓存加快后续构建）：

```bash
# 给脚本添加执行权限
chmod +x build_android_no_clean.sh

# 执行构建
./build_android_no_clean.sh
```

或者使用标准 buildozer 命令：

```bash
# 首次构建或需要清理缓存时
buildozer android debug
```

#### 3. 监控构建进度（可选）

在另一个终端窗口中运行：

```bash
chmod +x watch_build.sh
./watch_build.sh
```

### 构建输出

构建成功后，APK 文件将生成在 `bin/` 目录：
- 文件名: `tunnelmanager-0.1-arm64-v8a_armeabi-v7a-debug.apk`
- 大小: 约 34 MB
- 架构: arm64-v8a 和 armeabi-v7a

---

## 📦 APK 安装

### 方法 1: 使用 ADB

```bash
# 连接 Android 设备到电脑
adb devices

# 安装 APK
adb install bin/tunnelmanager-0.1-arm64-v8a_armeabi-v7a-debug.apk
```

### 方法 2: 手动安装

1. 将 APK 文件传输到 Android 设备
2. 在设备上打开文件管理器
3. 点击 APK 文件并允许安装
4. （首次安装需要在设置中允许"安装未知来源应用"）

---

## 🗂️ 项目结构

```
Tunnel/
├── buildozer.spec              # Android 打包配置
├── build_android_no_clean.sh   # 构建脚本（保留缓存）
├── watch_build.sh              # 构建监控脚本
├── README.md                   # 本文件
├── PROJECT_STRUCTURE.md        # 详细项目结构说明
│
├── src/                        # 源代码
│   └── main.py                 # Kivy 应用主程序
│
├── android/                    # Android 构建配置
│   └── local_recipes/          # 自定义构建配方
│       └── kivy/               # Kivy 兼容性补丁
│
└── bin/                        # 构建输出
    └── *.apk                   # 生成的 APK 文件
```

详细的项目结构说明请查看 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

---

## 🔍 技术细节

### 核心技术栈

- **UI 框架**: Kivy 2.2.1
- **Python 版本**: Python 3.11
- **Android 支持**: Python-for-Android
- **Java 桥接**: Pyjnius

### 已解决的关键问题

1. **Kivy 与 Cython 3.x 兼容性**
   - 创建了 8 个自定义补丁文件
   - 修复了回调函数、Python 3 API 等兼容性问题

2. **Gradle/Java 版本兼容性**
   - 升级 Gradle 从 8.0.2 到 8.5
   - 支持 Java 21 (class file major version 65)

3. **架构支持**
   - 同时支持 64 位 (arm64-v8a) 和 32 位 (armeabi-v7a) ARM 架构
   - 兼容性覆盖 99%+ 的 Android 设备

---

## 🐛 故障排查

### 构建失败

1. **检查 Java 版本**:
   ```bash
   java -version  # 确保是 OpenJDK 21
   ```

2. **清理缓存重新构建**:
   ```bash
   buildozer android clean
   buildozer android debug
   ```

3. **查看详细日志**:
   ```bash
   buildozer -v android debug
   ```

### 安装失败

1. **确保启用了"允许安装未知来源"**
2. **检查 Android 版本**: 需要 Android 5.0 (API 21) 或更高版本
3. **检查存储空间**: 需要至少 50 MB 可用空间

---

## 📄 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📞 联系方式

如有问题或建议，请通过 GitHub Issues 联系我们。

---

## 🔗 相关链接

- [Kivy 官方文档](https://kivy.org/doc/stable/)
- [Python-for-Android 文档](https://python-for-android.readthedocs.io/)
- [Buildozer 文档](https://buildozer.readthedocs.io/)
- [Cloudflare Tunnel 文档](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)

---

**注意**: 这是 Debug 版本，仅供测试使用。如需发布到应用商店，请构建 Release 版本并进行签名。