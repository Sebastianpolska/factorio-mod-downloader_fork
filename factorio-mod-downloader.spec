# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src\\factorio_mod_downloader\\__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('src/factorio_mod_downloader/assets', 'factorio_mod_downloader/assets')],
    hiddenimports=[],
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
    name='factorio-mod-downloader',
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
    icon=['src\\factorio_mod_downloader\\assets\\factorio_downloader.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='factorio-mod-downloader',
)
