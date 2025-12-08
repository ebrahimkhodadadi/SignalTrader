# Configuration Guide

This guide explains how to customize TelegramTrader's behavior through configuration files.

## 🌐 Language / زبان

- **[English](Configuration.md)** - English documentation
- **[فارسی](Configuration-fa.md)** - راهنمای پیکربندی فارسی

## Overview

TelegramTrader uses JSON configuration files to allow easy customization of:
- Message command keywords
- Price extraction regex patterns
- Other user-configurable settings

## Configuration Files Location

The application searches for configuration files in multiple locations in order of preference:

1. `config/` directory (recommended)
2. `configs/` directory
3. `settings/` directory
4. Project root directory

This allows flexibility in organizing configuration files. For example:

```
# Option 1: config/ directory (recommended)
config/
├── keywords.json          # Command keywords configuration
├── regex_patterns.json    # Price extraction patterns
└── development.json       # Application settings (git-ignored)

# Option 2: configs/ directory
configs/
├── keywords.json
└── regex_patterns.json

# Option 3: settings/ directory
settings/
├── keywords.json
└── regex_patterns.json

# Option 4: Project root
keywords.json
regex_patterns.json
```

## FileLoaderService Architecture

The `FileLoaderService` provides a centralized, reusable solution for file loading across the application:

- **Single Responsibility**: Handles only file discovery and loading operations
- **Multi-path Search**: Automatically searches multiple directories
- **Error Handling**: Graceful handling of missing files and parse errors
- **Comprehensive Logging**: Detailed logs showing which files were loaded and from where
- **Type Safety**: Support for JSON and text files with proper typing

### Usage in Code

```python
from Configure.file_loader import get_file_loader

# Get the service instance
file_loader = get_file_loader()

# Load JSON configuration
config = file_loader.load_json_file("keywords.json")

# Load text file
content = file_loader.load_text_file("readme.txt")

# Check if file exists
exists = file_loader.file_exists("settings.json")
```

## Command Keywords Configuration

Edit `config/keywords.json` to customize command keywords:

```json
{
  "message_commands": {
    "edit_keywords": [
      "edit",
      "edite", 
      "update",
      "modify"
    ],
    "delete_keywords": [
      "حذف",
      "delete",
      "close",
      "not a signal",
      "vip"
    ],
    "risk_free_keywords": [
      "فری",
      "risk free",
      "risk-free"
    ],
    "tp_keywords": [
      "tp",
      "هدف"
    ]
  },
  "description": {
    "edit_keywords": "Keywords used to detect edit commands in reply messages",
    "delete_keywords": "Keywords used to detect delete/close commands in reply messages", 
    "risk_free_keywords": "Keywords used to detect risk-free commands in reply messages",
    "tp_keywords": "Keywords used to detect take profit commands in reply messages"
  }
}
```

### Adding Custom Keywords

To add your own keywords:

1. Open `config/keywords.json`
2. Add your keywords to the appropriate array
3. Save the file
4. Restart the application

Example - Adding "modify" to edit commands:
```json
"edit_keywords": [
  "edit",
  "edite", 
  "update",
  "modify",
  "change"  // Your custom keyword
]
```

## Regex Patterns Configuration

Edit `config/regex_patterns.json` to customize price extraction patterns:

```json
{
  "price_extraction_patterns": {
    "first_price_patterns": [
      "(\\d+(?:\\.\\d+)?)",
      "(\\d+\\.\\d+)", 
      "@ (\\d+\\.\\d+)"
    ],
    "tp_patterns": [
      "tp\\s*\\d*[@:.-]?\\s*(\\d+\\.\\d+|\\d+)",
      "tp\\s*(?:\\d*\\s*:\\s*)?(\\d+\\.\\d+)",
      // ... more patterns
    ],
    "sl_patterns": [
      "sl\\s*:\\s*(\\d+\\.\\d+)",
      "sl\\s*:\\s*(\\d+\\.?\\d*)",
      // ... more patterns
    ]
  }
}
```

### Adding Custom Patterns

To add custom regex patterns:

1. Open `config/regex_patterns.json`
2. Add your pattern to the appropriate array
3. Test the pattern with sample messages
4. Save the file
5. Restart the application

Example - Adding a custom TP pattern:
```json
"tp_patterns": [
  "tp\\s*\\d*[@:.-]?\\s*(\\d+\\.\\d+|\\d+)",
  "target\\s*[:]?\\s*(\\d+\\.\\d+)"  // Your custom pattern
]
```

## Configuration Loading

The application loads configuration files at startup. If a configuration file is missing or invalid:

- The application will log a warning
- Default behavior will be used (if available)
- The application will continue to run

### Reloading Configuration

To reload configuration files without restarting:

1. Modify the configuration files
2. Restart the application

## Best Practices

1. **Backup Original Files**: Always backup original configuration files before making changes
2. **Test Changes**: Test configuration changes with sample messages
3. **Use Simple Keywords**: Keep keywords simple and easy to remember
4. **Validate Regex**: Test regex patterns thoroughly before deployment
5. **Version Control**: Keep configuration files in version control for tracking changes

## Troubleshooting

### Configuration Not Loading

If your configuration changes are not taking effect:

1. Check file syntax using a JSON validator
2. Ensure file is in the correct location (`config/` directory)
3. Check application logs for error messages
4. Verify file permissions

### Keywords Not Working

If command keywords are not being recognized:

1. Check that `config/keywords.json` exists and is valid
2. Verify keywords are in the correct arrays
3. Ensure keywords are lowercase (case-insensitive matching)
4. Restart the application

### Patterns Not Matching

If price extraction patterns are not working:

1. Test your regex pattern using online regex testers
2. Check that patterns are properly escaped
3. Verify the pattern exists in the correct category
4. Check application logs for pattern-related errors

## File Format Requirements

- **JSON Format**: All configuration files must be valid JSON
- **UTF-8 Encoding**: Files must be saved with UTF-8 encoding
- **No Comments**: JSON does not support comments
- **Proper Escaping**: Special characters must be properly escaped

## Security Considerations

- Configuration files can contain sensitive patterns
- Do not commit sensitive configuration to public repositories
- Use environment variables for sensitive settings
- Regularly review and update keyword lists