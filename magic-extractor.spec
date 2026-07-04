# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for magic-extractor (onedir build).
#
# bin/, data/ and config.ini are kept EXTERNAL to the exe (beside it) and
# user-updatable, so they are NOT bundled here. The frozen resolver in main.py
# uses the executable's directory as the base path, so after building you copy
# those folders next to the exe:
#
#   pyinstaller magic-extractor.spec
#   copy  src\bin      dist\magic-extractor\bin
#   copy  src\data     dist\magic-extractor\data
#   copy  src\config.ini dist\magic-extractor\config.ini
#
# (on Windows use xcopy /E for the folders). The exe then finds bin/data/config
# beside itself, and updating an extractor or the routing map is just a file swap.

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['src'],          # so the flat 'from formats import ...' etc. resolve
    binaries=[],
    datas=[],                # bin/data/config stay external, see header
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='magic-extractor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='magic-extractor',
)
