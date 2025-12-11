# Configuration Guide

This guide explains how to configure SignalTrader for your trading setup. The configuration is stored in a JSON file that defines all necessary parameters for provider integration (Telegram, etc.), MetaTrader connection, and trading behavior.

## Quick Setup

1. Create a `settings.json` file in the project root (or next to the executable for releases)
2. Copy the sample configuration below and modify the values for your setup
3. Ensure all required fields are filled correctly

## Getting Required Credentials

### Telegram API Credentials
1. Visit https://my.telegram.org/auth
2. Log in with your phone number
3. Go to "API development tools"
4. Create a new application to get `api_id` and `api_hash`

### Telegram Chat ID for Notifications
1. Start a chat with [@RawDataBot](https://t.me/RawDataBot) on Telegram
2. Send any message to get your chat ID
3. Use this ID in the `Notification.chatId` field

### MetaTrader Credentials
- Obtain server address, username, and password from your broker
- Ensure MetaTrader 5 terminal is installed and running

## Sample Configuration

```json
{
  "Telegram": {
    "api_id": 12345678,
    "api_hash": "abcdef1234567890abcdef1234567890",
    "channels": {
      "whiteList": ["trading_signals_channel", "forex_signals"],
      "blackList": ["spam_channel", "unreliable_signals"]
    }
  },
  "Notification": {
    "token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz123456789",
    "chatId": 123456789
  },
  "MetaTrader": {
    "server": "YourBroker-Server",
    "username": 123456,
    "password": "YourPassword",
    "path": "C:/Path/To/MetaTrader/terminal64.exe",
    "lot": "2%",
    "HighRisk": false,
    "SaveProfits": [25, 25, 25, 25],
    "AccountSize": 10000,
    "CloserPrice": 0.5,
    "expirePendinOrderInMinutes": 30,
    "ClosePositionsOnTrail": true,
    "SymbolMappings": {
      "XAUUSD": "XAUUSD",
      "EURUSD": "EURUSD"
    },
    "symbols": {
      "whiteList": ["EURUSD", "GBPUSD", "XAUUSD"],
      "blackList": ["JPYUSD", "exotics"]
    }
  },
  "Timer": {
    "start": "08:00",
    "end": "18:00"
  },
  "disableCache": false
}
```

## Configuration Sections

### Telegram Settings

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `api_id` | number | Yes | Telegram API ID from https://my.telegram.org |
| `api_hash` | string | Yes | Telegram API hash from https://my.telegram.org |
| `channels.whiteList` | array | No | Array of allowed channel usernames. If empty, all channels are allowed except blacklisted ones |
| `channels.blackList` | array | No | Array of blocked channel usernames |

**Channel Filtering Logic:**
- If `whiteList` is not empty, only messages from whitelisted channels are processed
- `blackList` always takes precedence (blocked channels are ignored)
- Channel usernames should not include the @ symbol

### Notification Settings

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `token` | string | Yes | Telegram bot token from [@BotFather](https://t.me/BotFather) |
| `chatId` | number | Yes | Chat ID for receiving notifications (use [@RawDataBot](https://t.me/RawDataBot)) |

### MetaTrader Settings

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `server` | string | Yes | MetaTrader server address (e.g., "ICMarkets-MT5") |
| `username` | number | Yes | Trading account number |
| `password` | string | Yes | Trading account password |
| `path` | string | Yes | Full path to MetaTrader terminal64.exe |
| `lot` | string/number | Yes | Position size. Use "X%" for percentage of account, or fixed number |
| `HighRisk` | boolean | No | Enable dual entry points (default: false) |
| `SaveProfits` | array | No | Profit saving percentages (default: []) |
| `AccountSize` | number | No | Account balance override (default: uses MT5 account balance) |
| `CloserPrice` | number | No | Price adjustment for entries (default: 0) |
| `expirePendinOrderInMinutes` | number | No | Pending order expiration in minutes (default: no expiration) |
| `SymbolMappings` | object | No | Map base symbols to broker-specific variants |
| `ClosePositionsOnTrail` | boolean | No | Whether to close positions during trailing stops (default: true) |
| `symbols.whiteList` | array | No | Array of allowed trading symbols. If empty, all symbols are allowed except blacklisted ones |
| `symbols.blackList` | array | No | Array of blocked trading symbols |

### Symbol Filtering

Symbol filtering allows you to control which trading instruments the bot will accept signals for:

```json
"symbols": {
  "whiteList": ["EURUSD", "GBPUSD", "XAUUSD"],
  "blackList": ["JPYUSD", "exotics"]
}
```

**Symbol Filtering Logic:**
- If `whiteList` is not empty, only signals for whitelisted symbols are processed
- `blackList` always takes precedence (signals for blacklisted symbols are ignored)
- Symbol names should match the format used in signals (e.g., "EURUSD", "XAUUSD")
- Filtering is case-insensitive

### Timer Settings (Optional)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `start` | string | No | Trading start time in HH:MM format (24-hour) |
| `end` | string | No | Trading end time in HH:MM format (24-hour) |

**Timer Behavior:**
- Trading is only allowed between `start` and `end` times
- Times should be in 24-hour format (e.g., "08:00", "18:00")
- If timer spans midnight, it will work correctly

## Advanced Configuration

### Symbol Mappings
Some brokers use different symbol names than standard ones. Use `SymbolMappings` to handle this:

```json
"SymbolMappings": {
  "XAUUSD": "XAUUSDm",    // Gold with micro lot suffix
  "EURUSD": "EURUSD!",    // EURUSD with broker suffix
  "US30": "US30"          // Dow Jones index
}
```

### Profit Saving Strategy
The `SaveProfits` array defines partial profit taking levels:

```json
"SaveProfits": [25, 25, 25, 25]
```

This means:
- Take 25% profit at first TP level, close 25% of position
- Take another 25% at second TP level, close another 25%
- And so on...

### Second Layer Cache Strategy
To disable database caching (for debugging or memory constraints):

```json
"disableCache": false
```
**Note:** Disabling cache may impact performance for large position histories

### Risk Management
- `lot`: "2%" means 2% of account balance per trade
- `HighRisk`: true enables two entry points for averaging
- `CloserPrice`: Adjusts entry price closer to current market price (useful for pending orders)
- `ClosePositionsOnTrail`: Controls whether positions are closed during trailing stops. Set to false to only adjust stop losses without closing positions

## Environment Variables

You can use environment variables for sensitive data:

Create a `.env` file:
```
ENV=production
MT5_PASSWORD=your_secure_password
TELEGRAM_API_HASH=your_api_hash
```

Then reference in settings.json:
```json
{
  "MetaTrader": {
    "password": "$MT5_PASSWORD"
  },
  "Telegram": {
    "api_hash": "$TELEGRAM_API_HASH"
  }
}
```

## Validation

The application will validate your configuration on startup. Common issues:

- Invalid Telegram API credentials
- Incorrect MetaTrader path
- Wrong chat ID format
- Invalid time format in Timer

Check the logs for detailed error messages if startup fails.