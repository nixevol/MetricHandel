#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
打包脚本 - 将MetricHandel打包为exe单文件
"""
import subprocess
import sys
from pathlib import Path


# noinspection PyUnusedImports
def main():
    """执行打包"""
    print("=" * 60)
    print("MetricHandel 打包工具")
    print("=" * 60)
    
    # 检查PyInstaller是否安装
    try:
        import PyInstaller
        print(f"✓ PyInstaller 已安装 (版本: {PyInstaller.__version__})")
    except ImportError:
        print("✗ PyInstaller 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller 安装完成")
    
    # 清理之前的构建文件
    print("\n清理之前的构建文件...")
    dist_dir = Path("dist")
    build_dir = Path("build")
    if dist_dir.exists():
        import shutil
        shutil.rmtree(dist_dir)
        print("✓ 已清理 dist 目录")
    if build_dir.exists():
        import shutil
        shutil.rmtree(build_dir)
        print("✓ 已清理 build 目录")
    
    # 执行打包
    print("\n开始打包...")
    print("-" * 60)
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "build.spec",
        "--clean",
        "--noconfirm"
    ]
    
    try:
        subprocess.check_call(cmd)
        print("-" * 60)
        print("\n✓ 打包完成！")
        print(f"\n可执行文件位置: {Path('dist/MetricHandel.exe').absolute()}")
        print("\n注意：")
        print("1. 首次运行exe时，程序会在exe同目录下创建必要的文件夹（Data、DB等）")
        print("2. 打包进exe的目录（自动解压）：")
        print("   - static/ (静态文件，从exe中自动解压)")
        print("3. 外部目录（需要手动准备或程序自动创建）：")
        print("   - Models/ (模型配置，需要手动创建并放入配置文件)")
        print("   - Scripts/ (SQL脚本，需要手动创建并放入脚本文件)")
        print("   - DB/ (数据库，程序自动创建)")
        print("   - Data/ (数据文件，程序自动创建)")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ 打包失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

