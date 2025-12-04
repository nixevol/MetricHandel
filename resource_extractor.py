#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
资源提取模块 - 从打包的exe中提取Models和Scripts目录
"""
import sys
import shutil
from pathlib import Path
import os


# noinspection PyUnresolvedReferences,PyProtectedMember
def get_resource_path():
    """获取资源路径（打包后的临时目录）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller打包后的情况
        # sys._MEIPASS是临时解压目录
        return Path(sys._MEIPASS)
    else:
        # 开发环境，使用当前目录
        return Path(__file__).parent


def extract_resources(target_models_path: Path, target_scripts_path: Path):
    """
    从打包的资源中提取Models和Scripts目录到目标位置
    
    Args:
        target_models_path: 目标Models目录路径
        target_scripts_path: 目标Scripts目录路径
    """
    # 只在打包后的环境中提取资源
    if not getattr(sys, 'frozen', False):
        return  # 开发环境不提取资源
    
    resource_path = get_resource_path()
    source_models = resource_path / "Models"
    source_scripts = resource_path / "Scripts"
    
    # 提取Models目录
    if source_models.exists() and source_models.is_dir():
        if not target_models_path.exists():
            # 目标目录不存在，直接复制整个目录
            shutil.copytree(source_models, target_models_path)
            print(f"已提取Models目录到: {target_models_path}")
        else:
            # 目标目录存在，只复制不存在的文件
            _copy_missing_files(source_models, target_models_path)
    
    # 提取Scripts目录
    if source_scripts.exists() and source_scripts.is_dir():
        if not target_scripts_path.exists():
            # 目标目录不存在，直接复制整个目录
            shutil.copytree(source_scripts, target_scripts_path)
            print(f"已提取Scripts目录到: {target_scripts_path}")
        else:
            # 目标目录存在，只复制不存在的文件
            _copy_missing_files(source_scripts, target_scripts_path)


def _copy_missing_files(source_dir: Path, target_dir: Path):
    """
    复制源目录中不存在于目标目录的文件
    
    Args:
        source_dir: 源目录
        target_dir: 目标目录
    """
    copied_count = 0
    
    for root, dirs, files in os.walk(source_dir):
        # 计算相对路径
        rel_path = Path(root).relative_to(source_dir)
        target_subdir = target_dir / rel_path
        
        # 创建目标子目录
        target_subdir.mkdir(parents=True, exist_ok=True)
        
        # 复制文件
        for file in files:
            source_file = Path(root) / file
            target_file = target_subdir / file
            
            # 只复制不存在的文件
            if not target_file.exists():
                shutil.copy2(source_file, target_file)
                copied_count += 1
    

