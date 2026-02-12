# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Watchtower Agent
Builds a lightweight .exe that handles screen capture + input control.

Build command:
    cd agent
    pyinstaller agent.spec
"""

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['agent_main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pystray._win32',      # Windows tray backend
        'PIL._tkinter_finder',
        'websockets',
        'mss',
        'mss.windows',
        'pyautogui',
        'pyautogui._pyautogui_win',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy/unnecessary modules
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'tkinter',  # We use it for setup only, but can exclude from bundle
        'unittest',
        'xml',
        'email',
        'http',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='WatchtowerAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,            # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,                # TODO: Add icon file
)
