import argparse
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
# TreeView 不再使用，已移除导入
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty, NumericProperty
from kivy.clock import Clock
from kivy.utils import platform as kivy_platform


class TunnelManager:
    """同时支持 GUI 与 CLI 的 Cloudflare Tunnel 管理器"""

    def __init__(self, use_gui: bool = True):
        self.use_gui = use_gui
        self.colors = {
            'bg': '#f5f6f7',
            'primary': '#2d8cff',
            'success': '#28a745',
            'danger': '#dc3545',
            'text': '#333333'
        }

        self.base_dir = self._resolve_base_dir()
        self.config_file = os.path.join(self.base_dir, "config.json")
        self.cloudflared_binary = self._resolve_cloudflared_binary()
        self.tunnels: List[Dict] = []

        if self.use_gui:
            self.root_layout = None
            self.setup_gui()
        else:
            self.root_layout = None

        self.load_config()
        if self.use_gui:
            self.refresh_tunnel_list()

    # -------------------------- 基础能力 --------------------------

    def _resolve_base_dir(self) -> str:
        if getattr(sys, "frozen", False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))

    def _resolve_cloudflared_binary(self) -> str:
        binary_name = "cloudflared.exe" if platform.system() == "Windows" else "cloudflared"
        bundled_path = os.path.join(self.base_dir, binary_name)
        if os.path.exists(bundled_path):
            return bundled_path
        system_path = shutil.which(binary_name)
        if system_path:
            return system_path
        return binary_name

    # -------------------------- 通用消息封装 --------------------------

    def _show_error(self, title: str, message: str) -> None:
        if self.use_gui:
            popup = Popup(title=title, content=Label(text=message), size_hint=(0.8, 0.4))
            popup.open()
        else:
            print(f"[{title}] {message}", file=sys.stderr)

    def _show_info(self, title: str, message: str) -> None:
        if self.use_gui:
            popup = Popup(title=title, content=Label(text=message), size_hint=(0.8, 0.4))
            popup.open()
        else:
            print(f"[{title}] {message}")

    def _ask_yes_no(self, title: str, message: str) -> bool:
        if self.use_gui:
            # 在实际应用中，这里应该实现一个确认对话框
            # 为了简化，我们暂时返回 True
            return True

        while True:
            answer = input(f"[{title}] {message} (y/n): ").strip().lower()
            if answer in {"y", "yes"}:
                return True
            if answer in {"n", "no"}:
                return False
            print("请输入 y 或 n")

    def _show_output_dialog(self, title: str, content: str) -> None:
        if self.use_gui:
            popup = Popup(title=title, content=Label(text=content or "（无输出）"), size_hint=(0.8, 0.6))
            popup.open()
        else:
            divider = "=" * 40
            print(f"{divider}\n{title}\n{divider}\n{content}\n{divider}")

    # -------------------------- Cloudflared 处理 --------------------------

    def _locate_cloudflared(self) -> Optional[str]:
        candidates = [
            self.cloudflared_binary,
            os.path.join(self.base_dir, os.path.basename(self.cloudflared_binary)),
        ]
        for candidate in candidates:
            if os.path.isabs(candidate) and os.path.exists(candidate):
                return candidate
        system_candidate = shutil.which(os.path.basename(self.cloudflared_binary))
        if system_candidate:
            return system_candidate
        return None

    def ensure_cloudflared_available(self) -> bool:
        located = self._locate_cloudflared()
        if located:
            self.cloudflared_binary = located
            return True

        confirm = self._ask_yes_no(
            "提示",
            "未找到 cloudflared，可自动从 Cloudflare 官方仓库下载，是否继续？"
        )
        if not confirm:
            return False

        if self.use_gui:
            # 在实际应用中，这里应该实现一个下载进度对话框
            # 为了简化，我们直接调用下载函数
            try:
                downloaded_path = self._download_cloudflared_binary()
                self._show_info("成功", f"cloudflared 已下载到: {downloaded_path}")
            except Exception as exc:
                self._show_error("错误", f"自动下载 cloudflared 失败: {exc}")
                return False
        else:
            def cli_progress(downloaded: int, total: int) -> None:
                if total:
                    percent = min(100.0, downloaded * 100 / total)
                    message = f"\r下载 cloudflared: {percent:5.1f}% ({downloaded // 1024}/{total // 1024} KB)"
                else:
                    message = f"\r已下载 cloudflared: {downloaded // 1024} KB (总大小未知)"
                sys.stdout.write(message)
                sys.stdout.flush()

            try:
                downloaded_path = self._download_cloudflared_binary(cli_progress)
                sys.stdout.write("\r下载 cloudflared: 100.0% 完成\n")
            except Exception as exc:
                sys.stdout.write("\n")
                self._show_error("错误", f"自动下载 cloudflared 失败: {exc}")
                return False

        if not downloaded_path:
            self._show_error("错误", "下载 cloudflared 失败: 未获得有效路径")
            return False

        self.cloudflared_binary = downloaded_path
        self._show_info("成功", f"cloudflared 已下载到: {downloaded_path}")
        return True

    def _download_cloudflared_binary(self, progress_callback=None) -> str:
        system = platform.system()
        machine = platform.machine().lower()
        suffix = self._build_download_suffix(system, machine)

        url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-{suffix}"
        target_name = 'cloudflared.exe' if system == 'Windows' else 'cloudflared'
        target_path = os.path.join(self.base_dir, target_name)

        os.makedirs(self.base_dir, exist_ok=True)
        if os.path.exists(target_path):
            os.remove(target_path)

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name

        downloaded = 0
        last_error = None
        attempt_urls = [url]

        if system == 'Darwin':
            attempt_urls = [
                f"https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-macos-amd64.tgz"
            ]

        for attempt, download_url in enumerate(attempt_urls, start=1):
            try:
                with urllib.request.urlopen(download_url, timeout=180) as response:
                    total_header = response.headers.get('Content-Length')
                    total_bytes = int(total_header) if total_header else 0
                    if progress_callback:
                        progress_callback(0, total_bytes)

                    with open(tmp_path, 'wb') as out_file:
                        while True:
                            chunk = response.read(8192)
                            if not chunk:
                                break
                            out_file.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(downloaded, total_bytes)

                shutil.move(tmp_path, target_path)
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

                if system != 'Windows':
                    os.chmod(
                        target_path,
                        os.stat(target_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                    )

                if progress_callback:
                    progress_callback(downloaded, downloaded or 1)

                return target_path
            except Exception as exc:
                last_error = exc
                downloaded = 0

        if os.path.exists(tmp_path):
            os.remove(tmp_path)

        raise RuntimeError(
            f"下载 cloudflared 失败: {last_error}。如果持续失败，可手动下载 {attempt_urls[-1]} 并放置于程序目录。"
        )

    def _build_download_suffix(self, system: str, machine: str) -> str:
        if system == 'Linux':
            arch_map = {
                'x86_64': 'linux-amd64',
                'amd64': 'linux-amd64',
                'aarch64': 'linux-arm64',
                'arm64': 'linux-arm64',
                'armv7l': 'linux-arm',
                'armv6l': 'linux-arm',
            }
            suffix = arch_map.get(machine)
            if not suffix:
                raise ValueError(f'暂不支持的 Linux 架构: {machine}')
            return suffix

        if system == 'Windows':
            arch_map = {
                'x86_64': 'windows-amd64.exe',
                'amd64': 'windows-amd64.exe',
                'arm64': 'windows-arm64.exe',
            }
            suffix = arch_map.get(machine)
            if not suffix:
                raise ValueError(f'暂不支持的 Windows 架构: {machine}')
            return suffix

        raise ValueError(f'暂未支持的系统: {system}')

    # -------------------------- GUI 构建 --------------------------

    def setup_gui(self) -> None:
        self.root_layout = BoxLayout(orientation='vertical')
        
        # 创建标题栏
        header = BoxLayout(size_hint_y=None, height=50)
        title = Label(text="CloudFlare Tunnel Manager", font_size=20, bold=True)
        status = Label(text="✓ 系统正常运行", color=(0.16, 0.65, 0.27, 1))  # success color
        header.add_widget(title)
        header.add_widget(status)
        self.root_layout.add_widget(header)
        
        # 创建隧道列表
        self.create_tunnel_list()
        
        # 创建控制面板
        self.create_control_panel()

    def create_tunnel_list(self) -> None:
        # 创建一个滚动视图来放置隧道列表
        scroll_view = ScrollView()
        self.tunnel_list_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=1)
        self.tunnel_list_layout.bind(minimum_height=self.tunnel_list_layout.setter('height'))
        
        # 添加列标题
        header_layout = BoxLayout(size_hint_y=None, height=40)
        columns = ["名称", "协议", "远程主机名", "映射到本地端口", "状态"]
        for col in columns:
            label = Label(text=col, bold=True)
            header_layout.add_widget(label)
        self.tunnel_list_layout.add_widget(header_layout)
        
        scroll_view.add_widget(self.tunnel_list_layout)
        self.root_layout.add_widget(scroll_view)

    def create_control_panel(self) -> None:
        control_panel = BoxLayout(size_hint_y=None, height=50, spacing=10, padding=10)
        
        add_btn = Button(text="添加隧道")
        add_btn.bind(on_press=self.show_add_dialog)
        
        edit_btn = Button(text="编辑隧道")
        edit_btn.bind(on_press=self.show_edit_dialog)
        
        delete_btn = Button(text="删除隧道")
        delete_btn.bind(on_press=self.delete_tunnel)
        
        help_label = Label(text="双击隧道列表项以启动/停止隧道", color=(0.47, 0.47, 0.47, 1))
        
        control_panel.add_widget(add_btn)
        control_panel.add_widget(edit_btn)
        control_panel.add_widget(delete_btn)
        control_panel.add_widget(help_label)
        
        self.root_layout.add_widget(control_panel)

    # -------------------------- 数据与业务逻辑 --------------------------

    def load_config(self) -> None:
        self.tunnels = []
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 支持旧的根为列表或根为字典的格式
                tunnels_data = data.get('tunnels', []) if isinstance(data, dict) else data
                self.tunnels = tunnels_data if isinstance(tunnels_data, list) else []

        except Exception as exc:
            self._show_error("错误", f"加载配置文件失败: {exc}")
            self.tunnels = []

        # 兼容旧配置，转换为新格式
        for t in self.tunnels:
            if 'url' in t and 'local_port' not in t:
                # 这是一个简化的转换，假设 url 格式为 proto://host:port
                try:
                    parts = t['url'].split(':')
                    if len(parts) > 1:
                        t['local_port'] = int(parts[-1])
                except (ValueError, IndexError):
                    t['local_port'] = 3389 # 转换失败时的默认值
            
            # 清理旧字段
            if 'url' in t:
                del t['url']
            if 'local_address' in t:
                del t['local_address']
            if 'remote_port' in t:
                del t['remote_port']

            # 为新记录提供默认值
            if 'protocol' not in t:
                t['protocol'] = 'rdp'
            if 'local_port' not in t:
                t['local_port'] = 3389

        if self.use_gui:
            self.refresh_tunnel_list()

    def save_config(self) -> None:
        try:
            payload: Dict[str, object] = {'tunnels': self.tunnels}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
        except Exception as exc:
            self._show_error("错误", f"保存配置文件失败: {exc}")

    def refresh_tunnel_list(self) -> None:
        if not self.use_gui or not hasattr(self, 'tunnel_list_layout'):
            return

        # 清除现有的隧道项（保留标题行）
        if len(self.tunnel_list_layout.children) > 1:
            for child in self.tunnel_list_layout.children[1:]:
                self.tunnel_list_layout.remove_widget(child)

        # 添加隧道数据
        for tunnel in self.tunnels:
            status_text = "运行中" if tunnel.get('process_pid') else "已停止"
            status_color = (0.16, 0.65, 0.27, 1) if tunnel.get('process_pid') else (0.86, 0.21, 0.27, 1)  # success or danger color
            
            # 创建一个隧道项布局
            tunnel_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            
            # 添加各个字段
            name_label = Label(text=tunnel.get('name', ''))
            protocol_label = Label(text=tunnel.get('protocol', 'rdp'))
            hostname_label = Label(text=tunnel.get('hostname', ''))
            port_label = Label(text=str(tunnel.get('local_port', '')))
            status_label = Label(text=status_text, color=status_color)
            
            tunnel_layout.add_widget(name_label)
            tunnel_layout.add_widget(protocol_label)
            tunnel_layout.add_widget(hostname_label)
            tunnel_layout.add_widget(port_label)
            tunnel_layout.add_widget(status_label)
            
            # 为隧道项添加点击事件
            tunnel_layout.bind(on_touch_down=self.on_tunnel_touch)
            
            # 将隧道项添加到列表中
            self.tunnel_list_layout.add_widget(tunnel_layout)

    def find_tunnel_index(self, name: str) -> Optional[int]:
        for idx, tunnel in enumerate(self.tunnels):
            if tunnel['name'] == name:
                return idx
        return None

    def _find_pid_by_port(self, port: int) -> Optional[int]:
        """根据端口号查找监听进程的 PID (仅限非 Windows 系统)"""
        if platform.system() == "Windows":
            # Windows 拥有不同的命令，例如 `netstat -aon | findstr <port>`。
            # 此处暂时不实现 Windows 的逻辑，因为 PID 存储是主要问题。
            return None

        if not shutil.which('lsof'):
            self._show_error("错误", "未找到 'lsof' 命令，无法通过端口号停止隧道。\n请安装 lsof (例如: sudo apt install lsof)")
            return None

        try:
            cmd = ['lsof', '-i', f':{port}', '-t']
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0 or not result.stdout.strip():
                return None
            
            pids = result.stdout.strip().split('\n')
            if pids:
                return int(pids[0])
        except (ValueError, IndexError):
            return None
        except Exception as exc:
            self._show_error("查找进程错误", f"通过端口 {port} 查找进程时出错: {exc}")
            return None
        return None

    def start_tunnel(self, index: int) -> bool:
        tunnel = self.tunnels[index]
        try:
            if not self.ensure_cloudflared_available():
                return False

            if platform.system() == "Windows":
                creationflags = subprocess.CREATE_NO_WINDOW
            else:
                creationflags = 0

            proto = (tunnel.get('protocol') or 'rdp').strip()
            local_port = tunnel.get('local_port')
            if not local_port:
                self._show_error("错误", "本地端口未配置，无法启动隧道")
                return False

            # 核心逻辑变更：--url 参数指向本地监听端口
            local_listen_url = f"{proto}://localhost:{local_port}"
            
            cmd = [
                self.cloudflared_binary,
                'access',
                proto,
                '--hostname',
                tunnel['hostname'],
                '--url',
                local_listen_url
            ]
            process = subprocess.Popen(cmd, shell=False, creationflags=creationflags)

            self.tunnels[index]['process_pid'] = process.pid
            self.save_config()
            self.refresh_tunnel_list()
            self._show_info("成功", f"隧道 {tunnel['name']} 已启动 (PID={process.pid})")
            return True
        except FileNotFoundError:
            binary_name = os.path.basename(self.cloudflared_binary)
            self._show_error("错误", f"找不到 {binary_name}，请确保它在系统 PATH 中或与程序在同一目录下。")
            return False
        except Exception as exc:
            self._show_error("错误", f"启动隧道失败: {exc}")
            return False

    def stop_tunnel(self, index: int) -> bool:
        tunnel = self.tunnels[index]
        pid_to_kill = None

        if platform.system() == "Windows":
            pid_to_kill = tunnel.get('process_pid')
        else:
            local_port = tunnel.get('local_port')
            if not local_port:
                self._show_error("错误", f"隧道 {tunnel['name']} 未配置本地端口，无法停止。")
                return False
            pid_to_kill = self._find_pid_by_port(local_port)

        if not pid_to_kill:
            self._show_info("提示", f"隧道 {tunnel['name']} 已经停止")
            if tunnel.get('process_pid') is not None:
                self.tunnels[index]['process_pid'] = None
                self.save_config()
                self.refresh_tunnel_list()
            return True

        try:
            if platform.system() == "Windows":
                subprocess.run(
                    ['taskkill', '/F', '/PID', str(pid_to_kill)],
                    shell=False, check=True, creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                subprocess.run(['kill', '-9', str(pid_to_kill)], shell=False, check=True)
            
            self.tunnels[index]['process_pid'] = None
            self.save_config()
            self.refresh_tunnel_list()
            self._show_info("成功", f"隧道 {tunnel['name']} 已停止")
            return True
        except subprocess.CalledProcessError:
            self.tunnels[index]['process_pid'] = None
            self.save_config()
            self.refresh_tunnel_list()
            self._show_info("提示", f"隧道 {tunnel['name']} 进程可能已不存在，状态已同步")
            return True
        except Exception as exc:
            self._show_error("错误", f"停止隧道时发生未知错误: {exc}")
            return False

    # -------------------------- GUI 事件处理 --------------------------

    def show_add_dialog(self, instance) -> None:
        # 在实际应用中，这里应该实现一个添加隧道的对话框
        # 为了简化，我们暂时添加一个默认隧道
        self.tunnels.append({
            'name': '新隧道',
            'protocol': 'rdp',
            'hostname': 'example.com',
            'local_port': 3389,
            'process_pid': None
        })
        self.save_config()
        self.refresh_tunnel_list()

    def show_edit_dialog(self, instance) -> None:
        # 在实际应用中，这里应该实现一个编辑隧道的对话框
        # 为了简化，我们暂时不做任何操作
        self._show_info("提示", "编辑功能尚未实现")

    def delete_tunnel(self, instance) -> None:
        # 在实际应用中，这里应该实现一个删除隧道的确认对话框
        # 为了简化，我们暂时删除第一个隧道
        if self.tunnels:
            if self.tunnels[0].get('process_pid'):
                self.stop_tunnel(0)
            del self.tunnels[0]
            self.save_config()
            self.refresh_tunnel_list()
            self._show_info("成功", "隧道已删除")
        else:
            self._show_info("提示", "没有可删除的隧道")

    def on_tunnel_touch(self, instance, touch):
        """处理隧道项的点击事件"""
        if instance.collide_point(*touch.pos):
            # 获取隧道项的索引
            index = self.tunnel_list_layout.children.index(instance) - 1  # 减去标题行
            if 0 <= index < len(self.tunnels):
                tunnel = self.tunnels[index]
                if tunnel.get('process_pid'):
                    self.stop_tunnel(index)
                else:
                    self.start_tunnel(index)
                return True
        return False

    def on_close(self) -> None:
        """Handles window closing to ensure all tunnels are stopped."""
        if self._ask_yes_no("退出确认", "确定要退出吗？所有正在运行的隧道都将被停止。"):
            for i in range(len(self.tunnels)):
                if self.tunnels[i].get('process_pid'):
                    self.stop_tunnel(i)


class TunnelApp(App):
    def build(self):
        self.manager = TunnelManager(use_gui=True)
        return self.manager.root_layout


# 登录功能已根据用户要求移除
class TunnelCLI:
    """命令行模式下的隧道管理器"""

    def __init__(self, manager: TunnelManager):
        self.manager = manager

    def run(self, argv: List[str]) -> None:
        parser = argparse.ArgumentParser(description="Cloudflare Tunnel 管理 CLI")
        subparsers = parser.add_subparsers(dest="command")

        subparsers.add_parser("list", help="列出所有隧道")

        add_parser = subparsers.add_parser("add", help="添加新隧道")
        add_parser.add_argument("name", help="连接名称")
        add_parser.add_argument("hostname", help="远程主机名 (例如 rdp.example.com)")
        add_parser.add_argument("local_port", type=int, help="要映射到的本地端口 (例如 3389)")
        add_parser.add_argument("--protocol", choices=['rdp', 'tcp', 'http', 'https', 'smb', 'ssh'], default='rdp', help="远程服务协议")

        update_parser = subparsers.add_parser("update", help="更新隧道配置")
        update_parser.add_argument("name", help="待更新的隧道名称")
        update_parser.add_argument("--new-name", help="新的连接名称")
        update_parser.add_argument("--hostname", help="新的远程主机名")
        update_parser.add_argument("--local-port", type=int, help="新的本地端口")
        update_parser.add_argument("--protocol", choices=['rdp', 'tcp', 'http', 'https', 'smb', 'ssh'], help="新的协议")

        delete_parser = subparsers.add_parser("delete", help="删除隧道")
        delete_parser.add_argument("name", help="隧道名称")

        start_parser = subparsers.add_parser("start", help="启动隧道")
        start_parser.add_argument("name", help="隧道名称")

        stop_parser = subparsers.add_parser("stop", help="停止隧道")
        stop_parser.add_argument("name", help="隧道名称")

        if not argv:
            args = parser.parse_args(["list"])
        else:
            args = parser.parse_args(argv)

        if not hasattr(args, "command") or not args.command:
            self.cmd_list(args)
            return

        handler = getattr(self, f"cmd_{args.command}")
        handler(args)

    # -------------------------- CLI 命令实现 --------------------------

    def cmd_list(self, _args) -> None:
        tunnels = self.manager.tunnels
        if not tunnels:
            print("暂无隧道配置")
            return

        headers = ["名称", "协议", "远程主机名", "本地端口", "状态", "PID"]
        rows = []
        for tunnel in tunnels:
            status = "运行中" if tunnel.get('process_pid') else "已停止"
            rows.append([
                tunnel.get('name', ''),
                tunnel.get('protocol', 'rdp'),
                tunnel.get('hostname', ''),
                str(tunnel.get('local_port', '')),
                status,
                str(tunnel.get('process_pid') or "-")
            ])

        widths = [len(h) for h in headers]
        for row in rows:
            for idx, cell in enumerate(row):
                widths[idx] = max(widths[idx], len(cell))

        def format_row(items):
            return "  ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(items))

        print(format_row(headers))
        print("  ".join('-' * w for w in widths))
        for row in rows:
            print(format_row(row))

    def cmd_add(self, args) -> None:
        if self.manager.find_tunnel_index(args.name) is not None:
            print(f"隧道 {args.name} 已存在", file=sys.stderr)
            sys.exit(1)

        self.manager.tunnels.append({
            'name': args.name,
            'protocol': args.protocol,
            'hostname': args.hostname,
            'local_port': args.local_port,
            'process_pid': None
        })
        self.manager.save_config()
        print(f"隧道 {args.name} 已添加")

    def cmd_update(self, args) -> None:
        index = self._require_index(args.name)
        tunnel = self.manager.tunnels[index]

        if args.new_name:
            if args.new_name != args.name and self.manager.find_tunnel_index(args.new_name) is not None:
                print(f"新名称 {args.new_name} 已存在", file=sys.stderr)
                sys.exit(1)
            tunnel['name'] = args.new_name
        if args.hostname:
            tunnel['hostname'] = args.hostname
        if args.local_port is not None:
            tunnel['local_port'] = args.local_port
        if args.protocol:
            tunnel['protocol'] = args.protocol

        self.manager.save_config()
        print(f"隧道 {tunnel['name']} 已更新")

    def cmd_delete(self, args) -> None:
        index = self._require_index(args.name)
        tunnel = self.manager.tunnels[index]
        if tunnel.get('process_pid'):
            self.manager.stop_tunnel(index)
        del self.manager.tunnels[index]
        self.manager.save_config()
        print(f"隧道 {tunnel['name']} 已删除")

    def cmd_start(self, args) -> None:
        index = self._require_index(args.name)
        self.manager.start_tunnel(index)

    def cmd_stop(self, args) -> None:
        index = self._require_index(args.name)
        self.manager.stop_tunnel(index)

    def cmd_login(self, args) -> None:
        # 登录功能已根据用户要求移除
        print("登录功能已移除。")

    # -------------------------- CLI 辅助方法 --------------------------

    def _require_index(self, name: str) -> int:
        index = self.manager.find_tunnel_index(name)
        if index is None:
            print(f"未找到名称为 {name} 的隧道", file=sys.stderr)
            sys.exit(1)
        return index


def main() -> None:
    raw_args = sys.argv[1:]
    force_gui = '--force-gui' in raw_args
    cli_flag = '--cli' in raw_args

    filtered_args = [arg for arg in raw_args if arg not in ('--cli', '--force-gui')]
    is_windows = platform.system() == "Windows"
    display_available = bool(os.environ.get('DISPLAY')) or is_windows
    use_cli = cli_flag or (not force_gui and not display_available)

    if use_cli:
        manager = TunnelManager(use_gui=False)
        cli = TunnelCLI(manager)
        cli.run(filtered_args)
    else:
        if filtered_args:
            print("GUI 模式下忽略的参数:", " ".join(filtered_args))
        TunnelApp().run()


if __name__ == "__main__":
    main()