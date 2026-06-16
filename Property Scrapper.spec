# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['G:\\99 acres\\99 acres  test - Copy\\app_tkinter.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['customtkinter', 'playwright', 'playwright.sync_api', 'pandas', 'openpyxl', 'extract_buy_data', 'extract_data', 'extract_buy_owner_details', 'extract_owner_details'],
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
    a.binaries,
    a.datas,
    [],
    name='Property Scrapper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
