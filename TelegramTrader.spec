# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect submodules and data files for MetaTrader and Telegram packages
metatrader_submodules = collect_submodules('MetaTrader')
telegram_submodules = collect_submodules('Telegram')

metatrader_data = collect_data_files('MetaTrader')
telegram_data = collect_data_files('Telegram')

# Combine all submodules and data files
all_hiddenimports = ['numpy'] + metatrader_submodules + telegram_submodules
all_datas = metatrader_data + telegram_data

a = Analysis(
    ['app\\runner.py'],
    pathex=[],
    binaries=[],
    datas=all_datas,
    hiddenimports=all_hiddenimports,
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
    name='TelegramTrader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
