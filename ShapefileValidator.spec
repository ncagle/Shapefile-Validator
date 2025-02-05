# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['shapefile_validator.py'],
    pathex=[],
    binaries=[('C:\\Users\\NatCagle\\Anaconda3\\envs\\shapefile-validator\\Lib\\site-packages\\pyogrio.libs\\gdal-debee5933f0da7bb90b4bcd009023377.dll', '.')],
    datas=[],
    hiddenimports=['geopandas', 'pyogrio._geometry'],
    hookspath=['.'],
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
    name='ShapefileValidator',
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
