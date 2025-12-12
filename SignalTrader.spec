# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect submodules and data files for all app packages
metatrader_submodules = collect_submodules('MetaTrader')
telegram_submodules = collect_submodules('Telegram')
database_submodules = collect_submodules('Database')
configure_submodules = collect_submodules('Configure')
providers_submodules = collect_submodules('Providers')
analayzer_submodules = collect_submodules('Analayzer')

# Collect data files
metatrader_data = collect_data_files('MetaTrader')
telegram_data = collect_data_files('Telegram')
database_data = collect_data_files('Database')
configure_data = collect_data_files('Configure')

# Combine all submodules and data files
all_hiddenimports = [
    'numpy',
    'MetaTrader5',
    'telethon',
    'discord',
    'loguru',
    'sqlite3',
    'requests',
] + metatrader_submodules + telegram_submodules + database_submodules + configure_submodules + providers_submodules + analayzer_submodules

all_datas = metatrader_data + telegram_data + database_data + configure_data

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
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SignalTrader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    icon='logo.ico',

    # IMPORTANT: Do NOT use UPX → reduces antivirus false positives
    upx=False,
    upx_exclude=[],

    runtime_tmpdir=None,

    # Keep console -> your app seems CLI-based
    console=True,

    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SignalTrader'
)
