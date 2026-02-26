# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

block_cipher = None

# Diretório base do projeto
BASE_DIR = os.path.abspath('.')

# Coleta arquivos de dados do jaraco.text (dentro de setuptools._vendor)
jaraco_datas = []
try:
    jaraco_datas = collect_data_files('jaraco.text', include_py_files=False)
except Exception:
    pass

# Coleta metadados do setuptools para evitar erros do pkg_resources
setuptools_datas = []
try:
    setuptools_datas = copy_metadata('setuptools')
except Exception:
    pass

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
    ('Pacientes', 'Pacientes'),
    ('Terapeutas', 'Terapeutas'),
]

# Adiciona dados do jaraco.text e metadados do setuptools
datas.extend(jaraco_datas)
datas.extend(setuptools_datas)

# Hidden imports para PyQt6, Pygame, BLE, etc.
hidden_imports = [
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'pygame',
    'bleak',
    'bleak.backends',
    'bleak.backends.winrt',
    'bleak.backends.winrt.scanner',
    'asyncio',
    'winrt',
    'winrt.windows',
    'winrt.windows.foundation',
    'winrt.windows.foundation.collections',
    'winrt.windows.devices',
    'winrt.windows.devices.bluetooth',
    'winrt.windows.devices.bluetooth.advertisement',
    'winrt.windows.devices.enumeration',
    'winrt.windows.storage',
    'winrt.windows.storage.streams',
    'numpy',
    'numpy._core',
    'numpy._core._multiarray_umath',
    'numpy._core._exceptions',
    'numpy._core._methods',
    'numpy._core._dtype_ctypes',
    'numpy._core._internal',
    'numpy.core',
    'numpy.core.multiarray',
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
