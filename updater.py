#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动更新模块 - 通过 Gitee API 检测和下载更新
启动时检查网络，有更新则下载并启动新版本
"""
import sys
import subprocess
import time
import socket
import winreg
from pathlib import Path
from typing import Optional, Dict, Tuple
from packaging import version
import requests


# noinspection PyBroadException,PyChainedComparisons,PyUnresolvedReferences,PyMethodMayBeStatic
class Updater:
    """自动更新管理器"""
    
    # 注册表路径
    REGISTRY_KEY = r"SOFTWARE\MetricHandel"
    REGISTRY_VALUE_VERSION = "LatestVersion"
    
    def __init__(self, gitee_repo: str, current_version: str, exe_name: str = "MetricHandel.exe"):
        """
        初始化更新管理器
        
        Args:
            gitee_repo: Gitee 仓库地址，格式：username/repo 或 https://gitee.com/username/repo
            current_version: 当前版本号（如：1.0.0）
            exe_name: 可执行文件名
        """
        # 解析 Gitee 仓库地址
        if gitee_repo.startswith('http'):
            # 从 URL 中提取用户名和仓库名
            # 处理格式：https://gitee.com/username/repo.git 或 https://gitee.com/username/repo
            parts = gitee_repo.rstrip('/').rstrip('.git').split('/')
            self.repo = f"{parts[-2]}/{parts[-1]}"
        else:
            # 处理格式：username/repo 或 username/repo.git
            self.repo = gitee_repo.rstrip('.git')
        
        self.api_base = f"https://gitee.com/api/v5/repos/{self.repo}"
        self.current_version = current_version
        self.exe_name = exe_name
        self.base_path = self._get_base_path()
        self.current_exe = self.base_path / self.exe_name
        
        # 初始化注册表
        self._init_registry()
    
    def _get_base_path(self) -> Path:
        """获取程序基础路径"""
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        else:
            return Path(__file__).parent
    
    def _init_registry(self):
        """初始化注册表（如果不存在则创建）"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_KEY, 0, winreg.KEY_READ)
            winreg.CloseKey(key)
        except FileNotFoundError:
            # 注册表项不存在，创建它并写入当前版本号
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_KEY)
                winreg.SetValueEx(key, self.REGISTRY_VALUE_VERSION, 0, winreg.REG_SZ, self.current_version)
                winreg.CloseKey(key)
            except Exception:
                pass
    
    def get_registry_version(self) -> Optional[str]:
        """从注册表获取最新版本号"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_KEY, 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, self.REGISTRY_VALUE_VERSION)
            winreg.CloseKey(key)
            return value
        except (FileNotFoundError, OSError):
            return None
    
    def set_registry_version(self, version_str: str):
        """将版本号写入注册表"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_KEY, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, self.REGISTRY_VALUE_VERSION, 0, winreg.REG_SZ, version_str)
            winreg.CloseKey(key)
        except Exception:
            pass
    
    def check_version_control(self) -> Tuple[bool, Optional[str]]:
        """
        检查注册表中的版本号与当前版本号
        
        Returns:
            tuple: (need_update: bool, registry_version: str or None)
            need_update: True 表示注册表版本号大于当前版本，需要更新
        """
        try:
            registry_version = self.get_registry_version()
            
            # 如果注册表没有版本号，写入当前版本号
            if registry_version is None:
                self.set_registry_version(self.current_version)
                return False, self.current_version
            
            # 如果当前版本号大于注册表的版本号，更新注册表
            if self._compare_versions(self.current_version, registry_version) > 0:
                self.set_registry_version(self.current_version)
                return False, self.current_version
            
            # 如果注册表的版本号大于当前版本号，需要更新
            if self._compare_versions(registry_version, self.current_version) > 0:
                return True, registry_version
            
            return False, registry_version
        except Exception:
            return False, None
    
    def check_network(self, timeout: int = 3) -> bool:
        """
        检查网络连接
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            bool: True 表示网络可用，False 表示无网络
        """
        try:
            # 尝试连接 Gitee
            socket.create_connection(("gitee.com", 443), timeout=timeout)
            return True
        except (socket.error, OSError):
            return False
    
    def check_update(self, timeout: int = 15) -> Tuple[bool, Optional[Dict]]:
        """
        检查是否有更新
        
        Args:
            timeout: 超时时间（秒），默认15秒
        
        Returns:
            tuple: (has_update: bool, latest_release_info: dict or None)
        """
        try:
            url = f"{self.api_base}/releases/latest"
            headers = {
                'User-Agent': 'MetricHandel-Updater/1.0'
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            release_data = response.json()
            # Gitee API 返回的 tag_name 格式可能不同
            latest_version = release_data.get('tag_name', '') or release_data.get('name', '')
            latest_version = latest_version.lstrip('vV')
            
            # 比较版本
            if latest_version and self._compare_versions(latest_version, self.current_version) > 0:
                return True, {
                    'version': latest_version,
                    'tag_name': release_data.get('tag_name', ''),
                    'name': release_data.get('name', ''),
                    'body': release_data.get('body', ''),
                    'published_at': release_data.get('created_at', ''),
                    'assets': release_data.get('assets', [])
                }
            return False, None
            
        except Exception:
            # 检查失败，返回 False
            return False, None
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """
        比较两个版本号
        
        Returns:
            int: 1 if v1 > v2, -1 if v1 < v2, 0 if v1 == v2
        """
        try:
            return version.parse(v1).compare(version.parse(v2))
        except Exception:
            # 如果版本号格式不正确，使用字符串比较
            return 1 if v1 > v2 else (-1 if v1 < v2 else 0)
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def _print_progress(self, downloaded: int, total: int, bar_length: int = 40):
        """打印下载进度条"""
        if total == 0:
            return
        
        percent = downloaded / total
        filled = int(bar_length * percent)
        bar = '=' * filled + '-' * (bar_length - filled)
        percent_text = f"{percent * 100:.1f}%"
        downloaded_text = self._format_size(downloaded)
        total_text = self._format_size(total)
        
        # 使用 \r 在同一行更新
        print(f"\r下载进度: [{bar}] {percent_text} ({downloaded_text}/{total_text})", end='', flush=True)
    
    def download_update(self, release_info: Dict) -> Optional[Path]:
        """
        下载更新文件到当前目录，文件名为 MetricHandel_版本号.exe
        
        Args:
            release_info: release 信息（从 check_update 获取）
        
        Returns:
            下载的文件路径，如果失败返回 None
        """
        try:
            # 查找 exe 文件资产
            assets = release_info.get('assets', [])
            exe_asset = None
            
            for asset in assets:
                if asset['name'] == self.exe_name or asset['name'].endswith('.exe'):
                    exe_asset = asset
                    break
            
            if not exe_asset:
                return None
            
            # Gitee API 的下载链接字段可能是 browser_download_url 或 download_url
            download_url = exe_asset.get('browser_download_url') or exe_asset.get('download_url') or exe_asset.get('url')
            if not download_url:
                return None
            
            # 下载文件到当前目录，文件名为 MetricHandel_版本号.exe
            new_version = release_info['version']
            new_exe_name = f"MetricHandel_{new_version}.exe"
            new_exe_path = self.base_path / new_exe_name
            
            print(f"\n开始下载更新: {new_exe_name}")
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 获取文件总大小
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 8192
            
            with open(new_exe_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # 更新进度条
                        self._print_progress(downloaded, total_size)
            
            # 验证下载是否完整
            if total_size > 0 and downloaded != total_size:
                print(f"\n下载不完整！期望大小: {self._format_size(total_size)}, 实际大小: {self._format_size(downloaded)}")
                # 删除不完整的文件
                try:
                    new_exe_path.unlink()
                except Exception:
                    pass
                return None
            
            # 验证文件是否存在且大小正确
            if not new_exe_path.exists():
                print(f"\n下载失败：文件不存在")
                return None
            
            actual_size = new_exe_path.stat().st_size
            if total_size > 0 and actual_size != total_size:
                print(f"\n下载不完整！期望大小: {self._format_size(total_size)}, 实际大小: {self._format_size(actual_size)}")
                # 删除不完整的文件
                try:
                    new_exe_path.unlink()
                except Exception:
                    pass
                return None
            
            # 下载完成，换行并显示完成信息
            print(f"\n下载完成: {self._format_size(downloaded)}")
            
            # 注意：版本号在检测到新版本时已经写入注册表，这里不需要再次写入
            
            return new_exe_path
            
        except Exception as e:
            print(f"\n下载失败: {str(e)}")
            # 下载失败时不写入注册表
            return None
    
    def launch_new_version_and_exit(self, new_exe_path: Path) -> bool:
        """
        启动新版本程序并退出当前程序
        
        Args:
            new_exe_path: 新版本程序的路径
        
        Returns:
            是否成功启动
        """
        try:
            # 验证文件是否存在且大小大于0
            if not new_exe_path.exists():
                print(f"更新文件不存在: {new_exe_path}")
                return False
            
            file_size = new_exe_path.stat().st_size
            if file_size == 0:
                print(f"更新文件大小为0，可能下载不完整")
                return False
            
            # 启动新版本程序（不使用 CREATE_NO_WINDOW，确保显示窗口）
            subprocess.Popen(
                [str(new_exe_path)],
                cwd=str(self.base_path)
            )
            
            # 等待一下确保新程序启动
            time.sleep(1)
            
            # 删除旧版本程序
            try:
                if self.current_exe.exists():
                    # 在 Windows 上，需要先重命名再删除，因为程序正在运行
                    if sys.platform == 'win32':
                        old_exe_backup = self.base_path / f"{self.exe_name}.old"
                        if old_exe_backup.exists():
                            old_exe_backup.unlink()
                        self.current_exe.rename(old_exe_backup)
                        # 使用批处理脚本延迟删除
                        self._create_delete_script(old_exe_backup)
                    else:
                        self.current_exe.unlink()
            except Exception as e:
                print(f"删除旧版本失败: {e}")
                # 即使删除失败，也继续退出
            
            return True
        except Exception as e:
            print(f"启动新版本失败: {str(e)}")
            return False
    
    def _create_delete_script(self, file_to_delete: Path):
        """创建延迟删除脚本（Windows）"""
        try:
            script_content = f'''@echo off
timeout /t 3 /nobreak >nul
del /F /Q "{file_to_delete}" >nul 2>&1
del /F /Q "%~f0" >nul 2>&1
'''
            script_file = self.base_path / "delete_old.bat"
            with open(script_file, 'w', encoding='gbk') as f:
                f.write(script_content)
            
            # 后台运行删除脚本
            subprocess.Popen(
                [str(script_file)],
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                cwd=str(self.base_path)
            )
        except Exception:
            pass
