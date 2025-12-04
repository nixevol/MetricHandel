# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# 获取项目根目录
project_root = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        ('static', 'static'),  # 静态文件目录（前端资源，只读）
        ('Models', 'Models'),  # 模型配置文件目录（首次运行时会提取到配置的目录）
        ('Scripts', 'Scripts'),  # SQL脚本目录（首次运行时会提取到配置的目录）
        ('config.ini', '.'),  # 配置文件模板
    ],
    hiddenimports=[
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.loops.uvloop',
        'pandas._libs.tslibs.timedeltas',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.tslibs.np_datetime',
        'openpyxl.cell._writer',
        'configparser',  # 配置文件解析
        'winreg',  # Windows 注册表操作
    ],
    hookspath=[],
    hooksconfig={
        'pydantic': {
            'exclude': ['pydantic.v1'],
        },
    },
    runtime_hooks=[],
    excludes=[
        'jinja2',  # 排除 jinja2（未使用，避免警告）
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MetricHandel',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 显示控制台窗口，方便查看日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 可以添加图标文件路径，如 'icon.ico'
)

