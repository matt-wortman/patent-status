# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Patent Status Tracker.

To build: pyinstaller PatentStatusTracker.spec
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Get the base directory
BASE_DIR = os.path.dirname(os.path.abspath(SPEC))

# Collect customtkinter data files (themes, etc.)
customtkinter_datas = collect_data_files('customtkinter')

# Analysis
a = Analysis(
    [os.path.join(BASE_DIR, 'main.py')],
    pathex=[BASE_DIR],
    binaries=[],
    datas=[
        (os.path.join(BASE_DIR, 'src'), 'src'),
        *customtkinter_datas,
    ],
    hiddenimports=[
        'keyring.backends.Windows',
        'customtkinter',
        'PIL',
        'PIL._tkinter_finder',
        'PIL._imagingtk',
        'sqlite3',
        'requests',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PyQt5',
        'PySide6',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Create PYZ archive
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create the executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PatentStatusTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress the executable
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Icon can be added here:
    # icon='icon.ico',
)
