# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

# Diretório base do projeto
BASE_DIR = os.path.abspath('.')

# Dados a serem incluídos no executável
datas = [
    ('assets', 'assets'),
    ('FlyBird/assets', 'FlyBird/assets'),
    ('FlyBird/data', 'FlyBird/data'),
    ('FlyBird/modules', 'FlyBird/modules'),
    ('FlyBird/__init__.py', 'FlyBird'),
    ('FlyBird/main_fb.py', 'FlyBird'),
    ('Modules', 'Modules'),
    ('config.json', '.'),
    ('calibrations', 'calibrations'),
]

# Hidden imports para PyQt6, Pygame, BLE, etc.
hidden_imports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'pygame',
    'bleak',
    'asyncio',
    'numpy',
    'pandas',
    'pyqtgraph',
    'serial',
    'serial.tools',
    'serial.tools.list_ports',
]

a = Analysis(
    ['main.py'],
    pathex=[BASE_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Marms',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Marms',
)
