#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置管理模块 - 读取和管理config.ini配置文件
"""
import configparser
import sys
from pathlib import Path


def get_base_path():
    """获取应用基础路径，支持打包后的情况"""
    if getattr(sys, 'frozen', False):
        # 打包后的情况
        base_path = Path(sys.executable).parent
    else:
        # 开发环境
        base_path = Path(__file__).parent
    return base_path


def normalize_path(path_str: str, default_name: str) -> Path:
    """
    规范化路径
    支持绝对路径（如：C:\\Test）和相对路径（如：./Models）
    如果路径为空或不存在，则使用程序当前目录下的默认文件夹
    
    Args:
        path_str: 配置中的路径字符串
        default_name: 默认文件夹名称（如：'Data'、'Models'等）
    
    Returns:
        Path对象
    """
    base_path = get_base_path()
    
    # 如果路径为空或只包含空白字符，使用默认路径
    if not path_str or not path_str.strip():
        return base_path / default_name
    
    path_str = path_str.strip()
    
    # 处理相对路径（以./或../开头，或不以盘符开头）
    if path_str.startswith('./') or path_str.startswith('../'):
        # 相对路径，基于程序目录
        return (base_path / path_str).resolve()
    elif len(path_str) >= 2 and path_str[1] == ':':
        # Windows绝对路径（如：C:\\Test）
        return Path(path_str)
    elif path_str.startswith('/'):
        # Unix绝对路径
        return Path(path_str)
    else:
        # 相对路径（如：Models），基于程序目录
        return (base_path / path_str).resolve()


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，如果为None则使用程序目录下的config.ini
        """
        self.base_path = get_base_path()
        
        if config_file is None:
            config_file = self.base_path / "config.ini"
        else:
            config_file = Path(config_file)
        
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        # 如果配置文件不存在，创建默认配置
        if not self.config_file.exists():
            self._create_default_config()
        
        # 读取配置
        self.config.read(self.config_file, encoding='utf-8')
        
        # 解析路径配置
        self._parse_paths()
        
        # 解析服务器配置
        self._parse_server()
    
    def _create_default_config(self):
        """创建默认配置文件"""
        default_config = """[Paths]
# 数据文件目录（存储上传的文件）
# 支持绝对路径（如：C:\\Data）或相对路径（如：./Data）
# 如果为空或不存在，则使用程序当前目录下的Data文件夹
Data = 

# 数据库目录（存储Data.db文件）
# 支持绝对路径（如：C:\\Database）或相对路径（如：./DB）
# 如果为空或不存在，则使用程序当前目录下的DB文件夹
DB = 

# 模型配置文件目录（存储JSON配置文件）
# 支持绝对路径（如：C:\\Models）或相对路径（如：./Models）
# 如果为空或不存在，则使用程序当前目录下的Models文件夹
Models = 

# SQL脚本目录（存储SQL脚本文件）
# 支持绝对路径（如：C:\\Scripts）或相对路径（如：./Scripts）
# 如果为空或不存在，则使用程序当前目录下的Scripts文件夹
Scripts = 

[Server]
# Web服务器端口
# 默认端口为8000
Port = 8000

# FastAPI日志输出控制
# 可选值：critical, error, warning, info, debug, trace
# 设置为 critical 或 error 可减少日志输出，默认不输出（critical）
# 如果需要查看详细日志，可以设置为 info 或 debug
LogLevel = critical
"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write(default_config)
    
    def _parse_paths(self):
        """解析路径配置"""
        if 'Paths' not in self.config:
            self.config.add_section('Paths')
        
        # 解析各个路径
        self.data_path = normalize_path(
            self.config.get('Paths', 'Data', fallback=''),
            'Data'
        )
        self.db_path = normalize_path(
            self.config.get('Paths', 'DB', fallback=''),
            'DB'
        )
        self.models_path = normalize_path(
            self.config.get('Paths', 'Models', fallback=''),
            'Models'
        )
        self.scripts_path = normalize_path(
            self.config.get('Paths', 'Scripts', fallback=''),
            'Scripts'
        )
    
    def _parse_server(self):
        """解析服务器配置"""
        if 'Server' not in self.config:
            self.config.add_section('Server')
        
        try:
            self.port = self.config.getint('Server', 'Port', fallback=8000)
            if self.port < 1 or self.port > 65535:
                print(f"警告：端口号 {self.port} 无效，使用默认端口 8000")
                self.port = 8000
        except (ValueError, configparser.NoOptionError):
            self.port = 8000
        
        # 解析日志级别配置
        valid_log_levels = ['critical', 'error', 'warning', 'info', 'debug', 'trace']
        log_level = self.config.get('Server', 'LogLevel', fallback='critical').lower()
        if log_level not in valid_log_levels:
            print(f"警告：日志级别 {log_level} 无效，使用默认级别 critical")
            self.log_level = 'critical'
        else:
            self.log_level = log_level
    
    def get_data_path(self) -> Path:
        """获取数据文件目录路径"""
        return self.data_path
    
    def get_db_path(self) -> Path:
        """获取数据库目录路径"""
        return self.db_path
    
    def get_db_file_path(self) -> Path:
        """获取数据库文件完整路径"""
        return self.db_path / "Data.db"
    
    def get_models_path(self) -> Path:
        """获取模型配置目录路径"""
        return self.models_path
    
    def get_scripts_path(self) -> Path:
        """获取SQL脚本目录路径"""
        return self.scripts_path
    
    def get_port(self) -> int:
        """获取Web服务器端口"""
        return self.port
    
    def get_log_level(self) -> str:
        """获取日志级别"""
        return self.log_level
    
    def ensure_directories(self):
        """确保所有必要的目录存在"""
        directories = [
            self.data_path,
            self.db_path,
            self.models_path,
            self.scripts_path
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def save(self):
        """保存配置到文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)

