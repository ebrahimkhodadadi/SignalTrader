# Telegram Manager Bot - Refactored Structure

## Overview

The `manager_bot` has been refactored from a monolithic 835-line file into a modular, maintainable package following **Single Responsibility Principle (SRP)** and **KISS (Keep It Simple, Stupid)** principles.

## Module Structure

```
app/Providers/telegram/manager_bot/
├── __init__.py              # Package exports
├── manager_bot.py           # Main bot orchestrator (60 lines)
├── handlers.py              # Command & callback handlers (130 lines)
├── views.py                 # UI display & message formatting (400 lines)
├── actions.py               # Trade operations (close, update SL/TP, delete) (65 lines)
├── input_handlers.py        # Keyboard input processing (100 lines)
└── helpers.py               # Database queries & utilities (45 lines)
```

## Module Responsibilities

### `manager_bot.py` - Orchestrator (60 lines)
**Responsibility:** Initialize bot, coordinate all managers, start/stop the application

**Key Methods:**
- `__init__()` - Initialize MetaTrader connection and create manager instances
- `start_monitoring()` - Register handlers and start polling
- `stop()` - Clean shutdown
- `from_settings()` - Factory method for creation from config

**Dependencies:** Settings, MetaTrader, HandlerManager, ViewManager, ActionManager, InputHandler

---

### `handlers.py` - Command & Callback Router (130 lines)
**Responsibility:** Process user commands and inline button clicks, route to appropriate views/actions

**Key Methods:**
- `handle_start()` - Process /start command → Show main menu
- `handle_callback()` - Route inline button clicks:
  - `signals` → `show_signal_list()`
  - `signal_{id}` → `show_signal_detail()`
  - `positions` → `show_position_list()`
  - `position_{ticket}` → `show_position_detail()`
  - `close_*`, `update_*`, `delete_*` → Action handlers
  - `tester`, `trade` → View display
- `handle_message()` - Route text messages based on user state:
  - `STATE_TESTER` → `handle_tester_input()`
  - `STATE_AWAITING_LOT` → `handle_lot_input()`
  - `STATE_AWAITING_SL` → `handle_sl_input()`
  - `STATE_AWAITING_TP` → `handle_tp_input()`
  - Default → Show main menu

**State Constants:**
```python
STATE_MAIN_MENU = "main_menu"
STATE_AWAITING_LOT = "awaiting_lot"
STATE_AWAITING_SL = "awaiting_sl"
STATE_AWAITING_TP = "awaiting_tp"
STATE_TESTER = "tester"
```

**Dependencies:** ViewManager, ActionManager, InputHandler

---

### `views.py` - UI Display Manager (400 lines)
**Responsibility:** Format and display all messages with inline buttons

**Key Methods:**
- `show_main_menu()` - Display main menu (4 buttons: Signals, Positions, Tester, Summary)
- `show_signal_list()` - Grouped signals by signal_id with position/order counts
- `show_signal_detail()` - Entry price, SL, TP, message link, action buttons
- `show_position_list()` - All MT5 positions/orders as buttons
- `show_position_detail()` - Position/order details with action buttons
- `show_tester()` - Signal tester input prompt
- `show_trade_summary()` - Account stats (balance, equity, margin, P&L)

**Button Architecture:**
- All views display inline buttons for main content
- Back buttons are reply keyboard (sent as separate message)
- Keyboard buttons only shown for custom input prompts

**Dependencies:** MetaTrader, database repositories, helpers

---

### `actions.py` - Trade Operations (65 lines)
**Responsibility:** Handle user-initiated trade actions

**Key Methods:**
- `handle_close_action()` - Close position (full, half, custom lot, risk-free)
- `handle_update_action()` - Update SL or TP (shows keyboard with presets + custom)
- `handle_delete_order()` - Delete pending order

**Note:** Close/Update implementations are TODO markers ready for implementation

**Dependencies:** MetaTrader, user_states

---

### `input_handlers.py` - Keyboard Input Processor (100 lines)
**Responsibility:** Parse and validate keyboard input (lot sizes, SL/TP values, signal text)

**Key Methods:**
- `handle_lot_input()` - Parse lot size from keyboard, validate float
- `handle_sl_input()` - Parse SL value from keyboard, validate float
- `handle_tp_input()` - Parse TP value from keyboard, validate float
- `handle_tester_input()` - Parse signal text using SignalParser, return formatted result

**Input Format:**
```
Lot sizes: "0.1", "0.5", "1.0", "2.0", "5.0", "10.0", or "Custom"
SL/TP: "0.5", "1.0", "1.5", "2.0", "2.5", "3.0", "5.0", or "Custom"
Signals: "EUR/USD BUY 1.2500 SL: 1.2450 TP: 1.2550, 1.2600"
```

**Dependencies:** SignalParser

---

### `helpers.py` - Database & Utilities (45 lines)
**Responsibility:** Query database, find linked signals and positions

**Key Functions:**
- `find_signal_by_ticket(ticket)` - Look up signal for MT5 ticket
  1. Get database position by ticket
  2. Extract signal_id from position
  3. Query signal repository
- `get_position_for_signal(meta_trader, signal_id)` - Get MT5 position for signal
  1. Get database position by signal_id
  2. Extract position_id
  3. Query MetaTrader

**Dependencies:** Database repositories, MetaTrader

---

## Data Flow Examples

### Signal List View
```
User clicks "📊 Active Signals" (inline button)
    ↓
handlers.handle_callback() → action="signals"
    ↓
views.show_signal_list()
    ↓
1. Get MT5 positions/orders
2. For each position/order:
   - Get ticket from MT5 object
   - Call helpers.find_signal_by_ticket(ticket)
   - Group by signal_id: signals_dict[signal_id] = {signal, positions[], orders[]}
3. Build grouped text display
4. Create inline button for each signal group
5. Send keyboard back button in separate message
```

### Position Detail → Close Custom Lot
```
User clicks "📉 Close Custom" (inline button)
    ↓
handlers.handle_callback() → action="close", close_type="lot"
    ↓
actions.handle_close_action()
    ↓
1. Set user_state = STATE_AWAITING_LOT
2. Send keyboard: [["0.1", "0.5", "1.0"], ["2.0", "5.0", "10.0"], ["Custom"]]
    ↓
User selects "2.0" (keyboard button)
    ↓
handlers.handle_message() → state=STATE_AWAITING_LOT
    ↓
input_handlers.handle_lot_input("2.0")
    ↓
1. Parse float: 2.0
2. Show success message
3. Reset state to POSITION_LIST
```

### Signal Tester
```
User clicks "🧪 Signal Tester" (inline button)
    ↓
views.show_tester()
    ↓
User sends: "EUR/USD BUY 1.2500 SL: 1.2450 TP: 1.2550, 1.2600"
    ↓
handlers.handle_message() → state=STATE_TESTER
    ↓
input_handlers.handle_tester_input()
    ↓
1. Call SignalParser.parse_message()
2. Unpack tuple: (action_type, symbol, first_price, second_price, take_profits, stop_loss)
3. Format TP list as comma-separated
4. Display parsed result
```

## State Machine

```
User joins
    ↓
STATE_MAIN_MENU (default)
    ├─→ "signals" → show signal list
    ├─→ "positions" → show position list
    ├─→ "tester" → STATE_TESTER
    └─→ "trade" → show trade summary

STATE_SIGNAL_LIST
    ├─→ signal_{id} → STATE_VIEWING_SIGNAL
    └─→ Back → STATE_MAIN_MENU

STATE_VIEWING_SIGNAL
    ├─→ "close_..._full" → Show success (TODO: implement)
    ├─→ "close_..._lot" → STATE_AWAITING_LOT
    ├─→ "update_..._sl" → STATE_AWAITING_SL
    ├─→ "update_..._tp" → STATE_AWAITING_TP
    └─→ Back → STATE_SIGNAL_LIST

STATE_POSITION_LIST
    ├─→ position_{ticket} → STATE_VIEWING_POSITION
    └─→ Back → STATE_MAIN_MENU

STATE_VIEWING_POSITION
    ├─→ "close_..._lot" → STATE_AWAITING_LOT
    ├─→ "update_..._sl" → STATE_AWAITING_SL
    ├─→ "update_..._tp" → STATE_AWAITING_TP
    ├─→ "delete_..." → (show success, back to list)
    └─→ Back → STATE_POSITION_LIST

STATE_TESTER
    └─→ (send signal text) → Show parsed result

STATE_AWAITING_LOT, STATE_AWAITING_SL, STATE_AWAITING_TP
    └─→ (send value) → Show confirmation, back to previous view
```

## Benefits of Refactoring

| Aspect | Before | After |
|--------|--------|-------|
| **File Size** | 835 lines | 60 (main) + 130 (handlers) + 400 (views) + 65 (actions) + 100 (input) + 45 (helpers) = ~800 lines distributed |
| **Single File** | monolithic | 7 focused files |
| **Testability** | Hard to test individual functions | Each module is independently testable |
| **Maintainability** | Changes to one feature affect whole file | Changes isolated to relevant modules |
| **Responsibility** | Bot class did everything | Each class has single responsibility |
| **Reusability** | Can't reuse helpers, views, or actions | Can import and reuse any module independently |
| **Debugging** | Hard to find which method | Clear module separation makes debugging faster |
| **Code Navigation** | 835 line file to scroll | Max 400 lines per file, clear structure |

## Adding New Features

### Example: Add "Close All" Implementation

1. **In `actions.py`:**
   ```python
   async def handle_close_action(self, query, user_id: int, identifier: int, close_type: str) -> None:
       if close_type == "full":
           # TODO → Implementation here
           result = await self.meta_trader.close_position(identifier)
   ```

2. **Test in isolation:**
   ```python
   import pytest
   from actions import ActionManager
   
   @pytest.mark.asyncio
   async def test_close_full():
       manager = ActionManager(meta_trader_mock, user_states)
       await manager.handle_close_action(...)
   ```

### Example: Add Risk-Free Feature

1. **In `actions.py` → `handle_close_action()`**
2. **In `helpers.py`** → Add `calculate_risk_free_sl()` if needed
3. **No changes to other modules!**

## Testing Each Module

```python
# Test helpers independently
from helpers import find_signal_by_ticket
signal = find_signal_by_ticket(12345)

# Test views independently  
from views import ViewManager
view = ViewManager(meta_trader, user_states)
await view.show_signal_detail(query, user_id, signal_id)

# Test actions independently
from actions import ActionManager
actions = ActionManager(meta_trader, user_states)
await actions.handle_close_action(query, user_id, identifier, "full")

# Test input handlers independently
from input_handlers import InputHandler
handler = InputHandler(user_states)
await handler.handle_tester_input(update, user_id, "EUR/USD BUY 1.2500...")
```

## Import Map

```
manager_bot.py (Orchestrator)
    ├── imports → handlers.py (HandlerManager)
    │                ├── uses → views.py (ViewManager)
    │                ├── uses → actions.py (ActionManager)
    │                └── uses → input_handlers.py (InputHandler)
    │
    ├── imports → views.py
    │                └── uses → helpers.py (find_signal_by_ticket, get_position_for_signal)
    │
    ├── imports → actions.py
    │                └── (uses MetaTrader directly)
    │
    └── imports → input_handlers.py
                     └── (no other local imports)
```

## Migration Notes

- Old file backed up as `manager_bot_old.py`
- All imports updated automatically (loader.py already used correct path)
- No breaking changes to Provider interface
- All functionality preserved, just organized differently
