#!/bin/bash
# 监控构建日志的关键信息

echo "监控构建进度..."
echo "按 Ctrl+C 停止监控"
echo "================================"

tail -f build.log | grep --line-buffered -E "(INFO|ERROR|WARNING|Applying patch|Building|Compiling|patching file|succeeded|FAILED|Exception)"