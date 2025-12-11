# Telegram Integration

This document covers how SignalTrader integrates with Telegram for signal monitoring, message processing, and notification delivery.

## Overview

The Telegram integration uses the Telethon library to create a client that monitors specified channels for trading signals and sends notifications about trading activities.

## Setup Requirements

### Telegram API Credentials

1. **Create Telegram Application**
   - Visit https://my.telegram.org/auth
   - Log in with your phone number
   - Navigate to "API development tools"
   - Create a new application

2. **Obtain API Keys**
   - `api_id`: Integer ID for your application
   - `api_hash`: String hash for authentication

3. **Configure Settings**
   ```json
   "Telegram": {
     "api_id": 12345678,
     "api_hash": "abcdef1234567890abcdef1234567890"
   }
   ```

### Notification Bot

1. **Create Bot**
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Use `/newbot` command
   - Follow instructions to create your bot
   - Save the bot token

2. **Get Chat ID**
   - Start a chat with [@RawDataBot](https://t.me/RawDataBot)
   - Send any message to receive your chat ID

3. **Configure Notifications**
   ```json
   "Notification": {
     "token": "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz",
     "chatId": 123456789
   }
   ```

## Channel Monitoring

### Channel Selection

The bot can monitor specific channels using whitelist/blacklist filtering:

```json
"channels": {
  "whiteList": ["trading_signals", "forex_pro"],
  "blackList": ["spam_signals", "unreliable_trader"]
}
```

**Filtering Logic:**
- If whitelist is not empty, only whitelisted channels are monitored
- Blacklist always takes precedence
- Channel usernames without @ symbol

### Message Types Handled

1. **New Messages**: Primary signal detection
2. **Edited Messages**: Signal modifications (SL/TP updates)
3. **Deleted Messages**: Position closures
4. **Reply Messages**: Special commands (edit, delete, risk-free)

## Message Processing

### Signal Detection
- Monitors all new messages in allowed channels
- Parses message content for trading signals
- Extracts: action, symbol, prices, risk levels

### Special Commands
Messages that reply to original signals can trigger actions:

- **Edit/Update**: Modify stop loss or take profit
- **Delete/Close**: Close positions
- **Half**: Close half position
- **Risk Free**: Move SL to entry price

### Message Validation
- Checks channel permissions
- Validates message format
- Prevents duplicate processing

## Notification System

### Types of Notifications

1. **Startup Notification**
   - Sent when bot starts
   - Includes Jalali datetime
   - Confirms successful initialization

2. **Trading Notifications**
   - New position opened
   - Position closed/modified
   - Error alerts
   - Profit/loss updates

3. **System Notifications**
   - Connection issues
   - Configuration errors
   - Trading restrictions (timer violations)

### Notification Format
```
sys: 2023-11-11 15:47:48 | mt: 2023-11-11 12:17:48
New BUY position opened for EURUSD
```

## Connection Management

### Auto-Reconnection
- Handles network interruptions
- Automatic retry with exponential backoff
- Maintains session persistence

### Error Handling
- **FloodWaitError**: Rate limiting (automatic delay)
- **AuthKeyError**: Authentication issues
- **NetworkMigrateError**: Server switches
- **ServerError**: Temporary server issues

### Session Management
- Uses `TelegramSession` for session persistence
- Automatic session recovery
- Secure credential storage

## Security Considerations

### API Security
- Never share `api_id` and `api_hash`
- Use environment variables for sensitive data
- Regenerate credentials if compromised

### Channel Access
- Only monitor trusted signal channels
- Use whitelist for production
- Regularly audit channel permissions

### Rate Limiting
- Respects Telegram's rate limits
- Implements delays between requests
- Handles flood wait errors gracefully

## Message Parsing Details

### Text Processing
- UTF-8 encoding/decoding
- Unicode normalization
- Emoji and formatting removal
- Persian/Arabic text support

### Link Extraction
- Generates message links for reference
- Supports both username and ID-based channels
- Creates permanent links to signals

### Chat ID Handling
- Supports various chat ID formats
- Handles channel, group, and private chat IDs
- Strips -100 prefixes for supergroups

## Monitoring and Logging

### Activity Logging
- All message processing logged
- Channel filtering decisions recorded
- Error conditions captured

### Performance Monitoring
- Message processing times
- Connection status
- Rate limiting events

## API Reference

### Telethon Documentation
- Official docs: https://docs.telethon.dev/
- Client creation: `TelegramClient()`
- Event handling: `@client.on(events.NewMessage)`

### Key Classes

#### TelegramClient
- Main client for Telegram API interaction
- Handles authentication and session management
- Provides async message handling

#### Event Handlers
- `events.NewMessage`: New message detection
- `events.MessageEdited`: Message modification handling
- `events.MessageDeleted`: Deletion processing

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify `api_id` and `api_hash`
   - Check phone number verification
   - Ensure application is not deleted

2. **Channel Access Denied**
   - Confirm bot is added to private channels
   - Check channel permissions
   - Verify channel username spelling

3. **Rate Limiting**
   - Reduce monitoring frequency
   - Add delays between operations
   - Monitor flood wait errors

4. **Message Not Processing**
   - Check whitelist/blacklist settings
   - Verify message format
   - Review parsing logs

### Debug Tips
- Enable verbose logging
- Test with public channels first
- Use [@RawDataBot](https://t.me/RawDataBot) for chat ID verification
- Monitor console output for errors

## Best Practices

### Production Setup
- Use dedicated Telegram application
- Implement proper error handling
- Monitor bot activity regularly
- Keep credentials secure

### Channel Management
- Regularly review monitored channels
- Update whitelist/blacklist as needed
- Monitor signal quality and reliability

### Performance
- Limit concurrent operations
- Implement proper async handling
- Monitor memory usage
- Clean up old sessions