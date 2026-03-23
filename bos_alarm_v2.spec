# -*- mode: python ; coding: utf-8 -*-
import os
import customtkinter
import certifi
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

ctk_path = os.path.dirname(customtkinter.__file__)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('Blaulicht.ico', '.'),
        ('_update.bat', '.'),
        ('setup.bat', '.'),
        ('config.example.json', '.'),
        (ctk_path, 'customtkinter'),
    ] + collect_data_files('certifi'),
    hiddenimports=[
        'pystray._win32',
        'PIL._tkinter_finder',
        'certifi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BOS Alarm',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='Blaulicht.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BOS Alarm',
)
