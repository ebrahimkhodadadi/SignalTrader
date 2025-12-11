# Building Releases

This guide explains how to build executable releases of SignalTrader for distribution.

## Prerequisites

- Python 3.8 or higher
- All project dependencies installed
- PyInstaller installed

```bash
pip install pyinstaller
```

## Build Methods

### Method 1: Using Existing Spec File

If `SignalTrader.spec` exists:

```bash
pyinstaller SignalTrader.spec
```

### Method 2: Creating New Build

For first-time builds or when spec file is missing:

```bash
# Basic executable
pyinstaller --onefile --console app/runner.py

# With custom name and icon
pyinstaller --onefile --console --name SignalTrader --icon=icon.ico app/runner.py
```

## Build Options Explained

### PyInstaller Flags

- `--onefile`: Creates a single executable file
- `--console`: Shows console window (recommended for debugging)
- `--name`: Custom executable name
- `--icon`: Application icon (optional)

### Alternative Builds

```bash
# Windowed application (no console)
pyinstaller --onefile --windowed --name SignalTrader app/runner.py

# Debug build with console
pyinstaller --onefile --console --debug=all --name SignalTrader app/runner.py
```

## Output

Build artifacts are created in the `dist/` directory:

```
dist/
└── SignalTrader.exe  # Your executable
```

## Distribution

### For End Users

1. **Create Release Package**
   ```
   SignalTrader/
   ├── SignalTrader.exe
   ├── settings.json      # User must create this
   └── README.txt         # Basic usage instructions
   ```

2. **Required User Setup**
   - User must create `settings.json` with their credentials
   - Place executable and settings in same directory
   - Ensure MetaTrader 5 is installed

### Configuration Template

Provide users with a template `settings.json`:

```json
{
  "Telegram": {
    "api_id": "YOUR_API_ID",
    "api_hash": "YOUR_API_HASH",
    "channels": {
      "whiteList": [],
      "blackList": []
    }
  },
  "Notification": {
    "token": "YOUR_BOT_TOKEN",
    "chatId": "YOUR_CHAT_ID"
  },
  "MetaTrader": {
    "server": "YOUR_BROKER_SERVER",
    "username": "YOUR_ACCOUNT_NUMBER",
    "password": "YOUR_PASSWORD",
    "path": "PATH_TO_METATRADER/terminal64.exe",
    "lot": "2%",
    "HighRisk": false
  }
}
```

## Troubleshooting Builds

### Common Issues

1. **Missing Dependencies**
   ```
   ERROR: Module 'xyz' not found
   ```
   Solution: Install all requirements first
   ```bash
   pip install -r requirements.txt
   ```

2. **Large Executable Size**
   - PyInstaller bundles all dependencies
   - Size is normal for Python applications
   - Consider `--exclude-module` for unused modules

3. **Antivirus False Positives**
   - Common with PyInstaller executables
   - Add to antivirus exclusions
   - Sign executable if distributing commercially

4. **Import Errors**
   - Ensure all imports work in development
   - Check relative import paths
   - Test executable in clean environment

### Optimization

```bash
# Exclude unnecessary modules
pyinstaller --onefile --exclude-module matplotlib --exclude-module numpy app/runner.py

# Use UPX compression (if UPX installed)
pyinstaller --onefile --upx-dir=/path/to/upx app/runner.py
```

## Advanced Build Configuration

### Custom Spec File

# Create `SignalTrader.spec` for advanced control:

```python
# SignalTrader.spec
import PyInstaller.config
PyInstaller.config.CONF['distpath'] = './dist'
PyInstaller.config.CONF['workpath'] = './build'

block_cipher = None

a = Analysis(
    ['app/runner.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
   name='SignalTrader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon='icon.ico'
)
```

### Including Data Files

If you need to include additional files:

```python
# In spec file
datas=[
    ('data/Symbols.json', 'data'),
    ('config/default.json', 'config')
],
```

## Testing Builds

### Pre-Release Checks

1. **Functionality Test**
   ```bash
   # Test executable with sample config
   ./dist/SignalTrader.exe
   ```

2. **Dependency Check**
   - Run on clean system
   - Test all features
   - Verify error handling

3. **Performance Test**
   - Monitor memory usage
   - Check startup time
   - Test concurrent operations

### Release Checklist

- [ ] Build successful without errors
- [ ] Executable runs on target systems
- [ ] All features work correctly
- [ ] Configuration validation works
- [ ] Error messages are clear
- [ ] File size is reasonable
- [ ] No sensitive data in executable

## Platform-Specific Notes

### Windows
- Use `terminal64.exe` path
- Ensure Visual C++ Redistributables
- Test on Windows 7+ (if supporting older versions)

### Linux/Mac
- Adjust MetaTrader path accordingly
- Test on target distributions
- Consider Wine for MetaTrader compatibility

## Version Management

### Version Information
Add version info to executable:

```python
# version.py
__version__ = "1.0.0"

# In runner.py
import version
print(f"SignalTrader v{version.__version__}")
```

### Release Naming
```
SignalTrader-v1.0.0-Windows.exe
SignalTrader-v1.0.0-Source.zip
```
