# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['ChroLens_Sorting1.2.py'],
    pathex=[],
    binaries=[],
    datas=[('umi_綠色.ico', '.'), ('update_manager.py', '.'), ('update_dialog.py', '.')],
    hiddenimports=['ttkbootstrap', 'json', 'threading', 'csv'],
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
    name='ChroLens_Sorting',
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
    icon=['umi_綠色.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ChroLens_Sorting',
)
