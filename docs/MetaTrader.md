# MetaTrader 5 Integration

This document explains how SignalTrader integrates with MetaTrader 5 (MT5) for automated trading execution, position management, and market data access.

## Overview

The MetaTrader integration provides a complete bridge between Telegram signal processing and live trading execution. It handles order placement, position monitoring, risk management, and profit taking strategies.

## Setup Requirements

### Prerequisites
- MetaTrader 5 terminal installed
- Trading account with broker
- Algorithmic trading enabled in MT5
- Terminal path correctly configured in `settings.json`

### Configuration
```json
"MetaTrader": {
  "path": "C:/Program Files/MetaTrader 5/terminal64.exe",
  "server": "YourBroker-Server",
  "username": 123456,
  "password": "YourPassword"
}
```

## Core Functions

### Connection Management
- **Login**: Establishes connection to MT5 terminal
- **Symbol Selection**: Ensures trading symbols are available in Market Watch
- **Connection Monitoring**: Automatic reconnection on failures

### Order Execution
- **Market Orders**: Immediate execution at current market price
- **Pending Orders**: Limit and stop orders with expiration
- **Order Types**: Buy/Sell, Buy Limit/Stop, Sell Limit/Stop

### Position Management
- **Open Positions**: Track and modify existing positions
- **Partial Closures**: Close portions of positions for profit taking
- **Stop Loss/Take Profit**: Dynamic adjustment of risk levels

## Key Classes and Methods

### MetaTrader Class

#### Initialization
```python
mt = MetaTrader(
    path="path/to/terminal64.exe",
    server="broker-server",
    user=123456,
    password="password"
)
```

#### Connection Methods
- `Login()`: Connect to MT5 terminal
- `CheckSymbol(symbol)`: Verify symbol availability
- `GetSymbols()`: Retrieve all available symbols

#### Trading Methods
- `OpenPosition()`: Place new orders
- `close_position()`: Close positions or cancel orders
- `update_stop_loss()`: Modify stop loss levels
- `close_half_position()`: Partial position closure

#### Market Data
- `get_current_price()`: Get bid/ask prices
- `get_open_positions()`: List active positions
- `get_pending_orders()`: List pending orders

## Trading Logic

### Order Type Determination
The system automatically determines order types based on entry price vs. current market price:

- **Market Order**: When entry price is at current market level (± threshold)
- **Limit Order**: When entry price is better than current market
- **Stop Order**: When entry price is worse than current market

### Price Validation
For certain symbols (especially XAUUSD), prices are validated and adjusted to match broker requirements:
- Corrects decimal places
- Handles broker-specific formatting
- Prevents invalid price submissions

### Lot Size Calculation
Supports both fixed and percentage-based position sizing:
```python
# Percentage of account balance
lot = "2%"  # 2% of account balance

# Fixed lot size
lot = 0.01  # Fixed 0.01 lots
```

## Risk Management

### Stop Loss Management
- Automatic SL adjustment for trailing stops
- Validation against broker tick sizes
- Support for both position and pending order SL

### Take Profit Strategy
- Multiple TP levels supported
- Partial profit taking at each level
- Configurable profit saving percentages

### Position Monitoring
- Real-time position tracking
- Automatic trailing stop adjustments
- Profit level detection and execution

## Advanced Features

### Trailing Stops
Automatically adjusts stop loss as profits increase:
1. Monitors position profit levels
2. Moves SL to next TP level when reached
3. Closes partial positions for profit locking

### Profit Saving
Configurable partial closures:
```json
"SaveProfits": [25, 25, 25, 25]
```
- Takes 25% profit at each TP level
- Reduces position size progressively

### Dual Entry Points
High-risk mode with two entry levels:
- Primary entry at signal price
- Secondary entry for averaging
- Separate risk calculation for each

## Error Handling

### Common Issues
- **Invalid Price**: Price too close/far from market
- **No Connection**: MT5 terminal not running
- **Symbol Not Found**: Symbol not available with broker
- **Insufficient Funds**: Account balance too low

### Error Codes
MT5 returns specific error codes:
- `10004`: Invalid request
- `10006`: Invalid price
- `10013`: Invalid volume
- `10015`: Invalid price (too close to market)
- `10016`: Invalid stops
- `10027`: Auto trading disabled

## Database Integration

Signals and positions are stored in SQLite:
- **Signals Table**: Stores parsed signal data
- **Positions Table**: Links MT5 tickets to signals
- **Query Methods**: Retrieve positions by signal ID, update SL/TP

## Monitoring and Logging

### Real-time Monitoring
- Continuous position checking
- Pending order management
- Automatic cleanup of expired orders

### Logging
- All trading actions logged with timestamps
- MT5 server time included in logs
- Error details captured for debugging

## API Reference

### Official MT5 Python API
- Full documentation: https://www.mql5.com/en/docs/python_metatrader5
- Order sending: `mt5.order_send()`
- Position queries: `mt5.positions_get()`
- Symbol info: `mt5.symbol_info()`

### SignalTrader Extensions
- Price validation for specific symbols
- Automatic order type determination
- Risk-based lot size calculation
- Advanced position management

## Troubleshooting

### Connection Issues
1. Verify MT5 terminal is running
2. Check terminal path in settings
3. Ensure algorithmic trading is enabled
4. Confirm broker server details

### Trading Errors
1. Check account balance
2. Verify symbol availability
3. Review price validation logic
4. Check for duplicate positions

### Performance
- Monitor CPU usage during high-frequency trading
- Adjust monitoring intervals if needed
- Consider broker-specific limitations