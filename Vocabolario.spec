# -*- mode: python ; coding: utf-8 -*-
import os
import customtkinter

customtkinter_path = os.path.dirname(customtkinter.__file__)

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=[('icon.png', '.'), ('wiki', 'wiki'), (customtkinter_path, 'customtkinter')],
    hiddenimports=['constants', 'db', 'tts', 'item_tab', 'tutor_tab', 'spaced_tab', 'settings_tab'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Vocabolario',
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
    icon=['icon.png'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Vocabolario',
)
app = BUNDLE(
    coll,
    name='Vocabolario.app',
    icon='icon.png',
    bundle_identifier=None,
)
