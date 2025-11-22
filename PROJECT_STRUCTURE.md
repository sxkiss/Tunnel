# Tunnel Manager - 项目结构说明

## 📁 项目目录结构

```
/home/sxkiss/Tunnel/
├── .gitignore                      # Git 忽略文件配置
├── buildozer.spec                  # Buildozer Android 打包配置文件
├── build_android_no_clean.sh       # Android 构建脚本（保留缓存）
├── watch_build.sh                  # 构建进度监控脚本
├── README.md                       # 项目说明文档
├── PROJECT_STRUCTURE.md            # 本文件 - 项目结构说明
│
├── src/                            # 源代码目录
│   └── main.py                     # Kivy 应用主程序（771行）
│
├── android/                        # Android 构建相关配置
│   └── local_recipes/              # 自定义 Python-for-Android recipes
│       └── kivy/                   # Kivy 自定义 recipe
│           ├── __init__.py         # Recipe 定义文件
│           ├── fix-weakproxy-python3.patch
│           ├── fix-gstplayer-python3.patch
│           ├── fix-context-instructions-python3.patch
│           ├── fix-opengl-python3.patch
│           ├── fix-img-sdl2-noexcept.patch
│           ├── fix-window-sdl2-event-filter.patch
│           ├── fix-window-sdl2-cpdef.patch
│           └── fix-window-sdl2-titlebar.patch
│
└── bin/                            # 编译输出目录
    └── tunnelmanager-0.1-arm64-v8a_armeabi-v7a-debug.apk  # Android APK 文件 (34MB)
```

## 📝 重要文件说明

### 核心文件

1. **buildozer.spec**
   - Android 应用打包配置文件
   - 定义应用名称、包名、权限、依赖等
   - 配置 NDK/SDK 版本和构建参数

2. **src/main.py**
   - Kivy 框架编写的移动应用主程序
   - 包含完整的隧道管理功能
   - 从 Tkinter 完全重写为移动端适配

3. **android/local_recipes/kivy/**
   - 自定义 Kivy recipe，解决 Cython 3.x 兼容性问题
   - 包含 8 个关键补丁文件
   - 修复 Python 3 和 Cython 3 的兼容性问题

### 构建脚本

1. **build_android_no_clean.sh**
   - Android 构建脚本（推荐使用）
   - 保留所有缓存，加快后续构建速度
   - 自动激活虚拟环境并安装依赖

2. **watch_build.sh**
   - 实时监控构建进度
   - 显示构建日志关键信息

## 🔧 已解决的技术问题

### 1. Kivy 2.2.1 与 Cython 3.x 兼容性
创建了 8 个补丁文件解决：
- Python 3 `__long__` 方法移除问题
- Cython 3 回调函数需要 `noexcept` 声明
- `cpdef` 变量声明问题

### 2. Gradle/Java 版本兼容性
- 修改 gradle wrapper 从 8.0.2 升级到 8.5
- 解决 Java 21 与旧版 Gradle 的兼容性问题

## 🚀 构建命令

### 首次构建或清理构建
```bash
buildozer android debug
```

### 快速构建（保留缓存）
```bash
./build_android_no_clean.sh
```

### 监控构建进度
```bash
./watch_build.sh
```

## 📱 APK 信息

- **文件名**: tunnelmanager-0.1-arm64-v8a_armeabi-v7a-debug.apk
- **大小**: 34 MB
- **架构**: arm64-v8a, armeabi-v7a
- **最低 API**: 21 (Android 5.0)
- **目标 API**: 31 (Android 12.0)
- **权限**: INTERNET, ACCESS_NETWORK_STATE

## 🗑️ 已清理的多余文件

以下文件已被删除以保持项目整洁：

### 旧的桌面版本文件
- `main.py` - 旧的 Tkinter 版本
- `TunnelManager.spec` - PyInstaller 配置
- `requirements.txt` - 桌面版依赖

### 过时的构建脚本
- `build.sh`, `build.ps1`
- `build_android.sh`, `build_android.ps1`
- `check_build.sh`, `monitor_build.sh`, `prepare_deps.sh`
- `install_python.bat`, `install_python.ps1`, `install_python.sh`

### 临时文件
- `build.log`, `gradle_debug.log`
- `pyjnius-1.6.1.tar.gz`

### android 目录中的重复文件
- `android/buildozer.spec`
- `android/main.py`
- `android/bin/`

## 📦 依赖管理

所有 Python 依赖通过 buildozer.spec 中的 `requirements` 字段管理：
```
requirements = python3,kivy==2.2.1,pyjnius
```

## 🔄 版本控制

项目使用 Git 进行版本控制，`.gitignore` 已配置忽略：
- `.buildozer/` - 构建缓存目录
- `.venv_android/` - Python 虚拟环境
- `bin/*.apk` - 编译输出文件
- 其他临时文件和日志

## 📌 注意事项

1. **不要删除** `.buildozer/` 目录，它包含重要的构建缓存
2. **保留** `android/local_recipes/kivy/` 目录，它包含关键的兼容性补丁
3. **首次构建** 需要下载大量依赖，建议使用稳定网络
4. **后续构建** 使用 `build_android_no_clean.sh` 可大幅提升速度

## 🎯 下一步

1. 在真实 Android 设备上测试 APK
2. 修复发现的 bug
3. 构建 Release 版本用于发布
4. 考虑添加应用图标和启动画面