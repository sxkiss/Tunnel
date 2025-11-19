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

import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText


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
        self.tree: Optional[ttk.Treeview] = None

        if self.use_gui:
            self.root = tk.Tk()
            self.root.title("CloudFlare Tunnel Manager")
            self.root.geometry("900x600")
            self.setup_styles()
            self.create_gui()
        else:
            self.root = None

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
            messagebox.showerror(title, message)
        else:
            print(f"[{title}] {message}", file=sys.stderr)

    def _show_info(self, title: str, message: str) -> None:
        if self.use_gui:
            messagebox.showinfo(title, message)
        else:
            print(f"[{title}] {message}")

    def _ask_yes_no(self, title: str, message: str) -> bool:
        if self.use_gui:
            return messagebox.askyesno(title, message)

        while True:
            answer = input(f"[{title}] {message} (y/n): ").strip().lower()
            if answer in {"y", "yes"}:
                return True
            if answer in {"n", "no"}:
                return False
            print("请输入 y 或 n")

    def _show_output_dialog(self, title: str, content: str) -> None:
        if self.use_gui:
            dialog = tk.Toplevel(self.root)
            dialog.title(title)
            dialog.geometry("640x480")
            dialog.transient(self.root)
            dialog.grab_set()

            text_area = ScrolledText(dialog, wrap=tk.WORD)
            text_area.insert(tk.END, content or "（无输出）")
            text_area.configure(state=tk.DISABLED)
            text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=10)
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
            progress_dialog = DownloadProgressDialog(self.root)
            result: Dict[str, Optional[str]] = {"path": None, "error": None}
            done_flag = tk.BooleanVar(value=False)

            def worker() -> None:
                try:
                    path = self._download_cloudflared_binary(progress_dialog.update_progress)
                    result["path"] = path
                except Exception as exc:  # noqa: BLE001
                    result["error"] = str(exc)
                finally:
                    self.root.after(0, lambda: (progress_dialog.close(), done_flag.set(True)))

            threading.Thread(target=worker, daemon=True).start()
            self.root.wait_variable(done_flag)

            if result["error"]:
                self._show_error("错误", f"自动下载 cloudflared 失败: {result['error']}")
                return False

            downloaded_path = result["path"]
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
            except Exception as exc:  # noqa: BLE001
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

    def setup_styles(self) -> None:
        style = ttk.Style()
        style.configure('Custom.TFrame', background=self.colors['bg'])
        style.configure('Custom.TButton', padding=5, background=self.colors['primary'])
        style.configure(
            'Custom.Treeview',
            background='white',
            fieldbackground='white',
            rowheight=30,
            anchor=tk.CENTER
        )
        style.configure('Custom.Treeview.Heading', anchor=tk.CENTER)

    def create_gui(self) -> None:
        self.main_frame = ttk.Frame(self.root, style='Custom.TFrame')
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.create_header()
        self.create_tunnel_list()
        self.create_control_panel()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_header(self) -> None:
        header = ttk.Frame(self.main_frame, style='Custom.TFrame')
        header.pack(fill=tk.X, pady=(0, 20))

        title = ttk.Label(
            header,
            text="CloudFlare Tunnel Manager",
            font=('Helvetica', 16, 'bold'),
            background=self.colors['bg']
        )
        title.pack(side=tk.LEFT)

        status = ttk.Label(
            header,
            text="✓ 系统正常运行",
            foreground=self.colors['success'],
            background=self.colors['bg']
        )
        status.pack(side=tk.RIGHT)

    def create_tunnel_list(self) -> None:
        list_frame = ttk.Frame(self.main_frame, style='Custom.TFrame')
        list_frame.pack(fill=tk.BOTH, expand=True)

        # 增加 protocol 与 local_address 列
        columns = ("name", "protocol", "hostname", "local_port", "status")
        self.tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show='headings',
            style='Custom.Treeview'
        )

        column_configs = {
            "name": ("名称", 150),
            "protocol": ("协议", 80),
            "hostname": ("远程主机名", 280),
            "local_port": ("映射到本地端口", 150),
            "status": ("状态", 100)
        }

        for col, (text, width) in column_configs.items():
            self.tree.heading(col, text=text, anchor=tk.CENTER)
            self.tree.column(col, width=width, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind('<Double-1>', self.on_tunnel_double_click)

    def create_control_panel(self) -> None:
        control_frame = ttk.Frame(self.main_frame, style='Custom.TFrame')
        control_frame.pack(fill=tk.X, pady=(20, 0))

        left_buttons_frame = ttk.Frame(control_frame, style='Custom.TFrame')
        left_buttons_frame.pack(side=tk.LEFT)

        ttk.Button(
            left_buttons_frame,
            text="添加隧道",
            command=self.show_add_dialog,
            style='Custom.TButton'
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            left_buttons_frame,
            text="编辑隧道",
            command=self.show_edit_dialog,
            style='Custom.TButton'
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            left_buttons_frame,
            text="删除隧道",
            command=self.delete_tunnel,
            style='Custom.TButton'
        ).pack(side=tk.LEFT, padx=5)

        # 登录功能已移除

        help_label = ttk.Label(
            control_frame,
            text="双击隧道列表项以启动/停止隧道",
            background=self.colors['bg'],
            foreground="#777777"
        )
        help_label.pack(side=tk.LEFT, padx=10)

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
        if not self.use_gui or not self.tree:
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        for tunnel in self.tunnels:
            status_text = "运行中" if tunnel.get('process_pid') else "已停止"
            tag = "running" if tunnel.get('process_pid') else "stopped"
            values = (
                tunnel.get('name', ''),
                tunnel.get('protocol', 'rdp'),
                tunnel.get('hostname', ''),
                str(tunnel.get('local_port', '')),
                status_text
            )
            self.tree.insert('', tk.END, values=values, tags=(tag,))

        self.tree.tag_configure('running', foreground=self.colors['success'])
        self.tree.tag_configure('stopped', foreground=self.colors['danger'])

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

    # 登录功能已根据用户要求移除

    # -------------------------- GUI 事件处理 --------------------------
    # -------------------------- GUI 事件处理 --------------------------

    def show_add_dialog(self) -> None:
        dialog = TunnelDialog(self.root, "添加隧道")
        if dialog.result:
            self.tunnels.append(dialog.result)
            self.save_config()
            self.refresh_tunnel_list()

    def show_edit_dialog(self) -> None:
        selected = self.tree.selection() if self.tree else []
        if not selected:
            self._show_info("提示", "请先选择要编辑的隧道")
            return

        index = self.tree.index(selected[0])
        dialog = TunnelDialog(self.root, "编辑隧道", self.tunnels[index])
        if dialog.result:
            self.tunnels[index] = dialog.result
            self.save_config()
            self.refresh_tunnel_list()

    def delete_tunnel(self) -> None:
        selected = self.tree.selection() if self.tree else []
        if not selected:
            self._show_info("提示", "请先选择要删除的隧道")
            return

        if not self._ask_yes_no("确认", "确定要删除选中的隧道吗？"):
            return

        index = self.tree.index(selected[0])
        if self.tunnels[index].get('process_pid'):
            self.stop_tunnel(index)
        del self.tunnels[index]
        self.save_config()
        self.refresh_tunnel_list()

    def on_tunnel_double_click(self, _event) -> None:
        selected_items = self.tree.selection() if self.tree else []
        if selected_items:
            item = selected_items[0]
            index = self.tree.index(item)
            if self.tunnels[index].get('process_pid'):
                self.stop_tunnel(index)
            else:
                self.start_tunnel(index)

    def on_close(self) -> None:
        """Handles window closing to ensure all tunnels are stopped."""
        if self._ask_yes_no("退出确认", "确定要退出吗？所有正在运行的隧道都将被停止。"):
            for i in range(len(self.tunnels)):
                if self.tunnels[i].get('process_pid'):
                    self.stop_tunnel(i)
            self.root.destroy()

    def run(self) -> None:
        if not self.use_gui:
            raise RuntimeError("CLI 模式下无法调用 run()")
        self.root.mainloop()


class TunnelDialog:
    """GUI 下使用的隧道配置对话框"""

    def __init__(self, parent, title, tunnel=None):
        self.result = None

        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.geometry("460x360")
        dialog.transient(parent)
        dialog.grab_set()

        dialog.geometry("460x280")

        # 名称
        ttk.Label(dialog, text="连接名称:").grid(row=0, column=0, padx=8, pady=6, sticky='w')
        name_entry = ttk.Entry(dialog, width=35)
        name_entry.grid(row=0, column=1, padx=8, pady=6, sticky='w')

        # 协议
        ttk.Label(dialog, text="远程协议:").grid(row=1, column=0, padx=8, pady=6, sticky='w')
        protocol_cb = ttk.Combobox(dialog, values=['rdp', 'tcp', 'http', 'https', 'smb', 'ssh'], state='readonly', width=33)
        protocol_cb.grid(row=1, column=1, padx=8, pady=6, sticky='w')

        # 远程主机名
        ttk.Label(dialog, text="远程主机名:").grid(row=2, column=0, padx=8, pady=6, sticky='w')
        hostname_entry = ttk.Entry(dialog, width=35)
        hostname_entry.grid(row=2, column=1, padx=8, pady=6, sticky='w')

        # 本地端口
        ttk.Label(dialog, text="映射到本地端口:").grid(row=3, column=0, padx=8, pady=6, sticky='w')
        local_port_entry = ttk.Entry(dialog, width=35)
        local_port_entry.grid(row=3, column=1, padx=8, pady=6, sticky='w')

        if tunnel:
            name_entry.insert(0, tunnel.get('name', ''))
            protocol_cb.set(tunnel.get('protocol', 'rdp'))
            hostname_entry.insert(0, tunnel.get('hostname', ''))
            local_port_entry.insert(0, str(tunnel.get('local_port', '3389')))
        else:
            protocol_cb.set('rdp')
            local_port_entry.insert(0, '3389')

        def save():
            try:
                port_str = local_port_entry.get().strip()
                self.result = {
                    'name': name_entry.get().strip(),
                    'protocol': protocol_cb.get().strip() or 'rdp',
                    'hostname': hostname_entry.get().strip(),
                    'local_port': int(port_str) if port_str else None,
                    'process_pid': tunnel.get('process_pid') if tunnel else None
                }
                if not all(self.result[k] for k in ['name', 'protocol', 'hostname']) or self.result['local_port'] is None:
                    messagebox.showerror("错误", "所有字段均为必填项", parent=dialog)
                    return
                dialog.destroy()
            except (ValueError, TypeError):
                messagebox.showerror("错误", "本地端口必须是一个有效的数字", parent=dialog)

        ttk.Button(dialog, text="保存", command=save).grid(row=4, column=0, columnspan=2, pady=20)
        dialog.wait_window()


class DownloadProgressDialog:
    """cloudflared 下载进度对话框"""

    def __init__(self, parent: tk.Tk):
        self.top = tk.Toplevel(parent)
        self.top.title("下载 cloudflared")
        self.top.geometry("420x180")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.protocol("WM_DELETE_WINDOW", lambda: None)

        ttk.Label(self.top, text="正在下载 Cloudflare 官方客户端……").pack(pady=(15, 10))

        self.progress = ttk.Progressbar(self.top, mode='determinate', length=320)
        self.progress.pack(pady=5)

        self.status_label = ttk.Label(self.top, text="准备下载…")
        self.status_label.pack(pady=(0, 10))

        self._indeterminate = False

    def update_progress(self, downloaded: int, total: int) -> None:
        def _update() -> None:
            if total:
                if self._indeterminate:
                    self.progress.stop()
                    self.progress.config(mode='determinate')
                    self._indeterminate = False
                self.progress.config(maximum=total, value=downloaded)
                percent = min(100.0, downloaded * 100 / total) if total else 0.0
                self.status_label.config(
                    text=f"已下载 {percent:.1f}% ({downloaded // 1024}/{total // 1024} KB)"
                )
            else:
                if not self._indeterminate:
                    self.progress.config(mode='indeterminate')
                    self.progress.start(10)
                    self._indeterminate = True
                self.status_label.config(text=f"已下载 {downloaded // 1024} KB (总大小未知)")

        self.top.after(0, _update)

    def close(self) -> None:
        def _close() -> None:
            if self._indeterminate:
                self.progress.stop()
            self.top.grab_release()
            self.top.destroy()

        self.top.after(0, _close)




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
    display_available = bool(os.environ.get('DISPLAY'))
    use_cli = cli_flag or (not force_gui and not display_available)

    if use_cli:
        manager = TunnelManager(use_gui=False)
        cli = TunnelCLI(manager)
        cli.run(filtered_args)
    else:
        if filtered_args:
            print("GUI 模式下忽略的参数:", " ".join(filtered_args))
        manager = TunnelManager(use_gui=True)
        manager.run()


if __name__ == "__main__":
    main()
