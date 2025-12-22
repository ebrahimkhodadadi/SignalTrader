"""
Helper utilities for fetching and analyzing historical trading data
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import MetaTrader5 as mt5
from Database.database_manager import db_manager


def get_date_range_timestamps(range_type: str, from_date: datetime = None, to_date: datetime = None) -> Tuple[datetime, datetime]:
    """
    Get timestamp range based on type (today, yesterday, or custom)

    Uses MT5 broker time instead of server time to ensure correct date ranges

    Args:
        range_type: "today", "yesterday", or "custom"
        from_date: Start date for custom range
        to_date: End date for custom range

    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    # Get broker's current time from MT5 instead of server time
    try:
        account_info = mt5.account_info()
        if account_info and hasattr(account_info, 'server_time'):
            # server_time is a timestamp (seconds since epoch)
            now = datetime.fromtimestamp(account_info.server_time)
            logger.info(f"Using MT5 broker time: {now}")
        else:
            # Fallback to system time
            now = datetime.now()
            logger.warning("MT5 broker time not available, using system time")
    except Exception as e:
        logger.warning(f"Error getting MT5 broker time: {e}, using system time")
        now = datetime.now()

    if range_type == "today":
        start = datetime(now.year, now.month, now.day, 0, 0, 0)
        end = datetime(now.year, now.month, now.day, 23, 59, 59)
    elif range_type == "yesterday":
        yesterday = now - timedelta(days=1)
        start = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0)
        end = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
    elif range_type == "custom" and from_date and to_date:
        start = from_date
        end = to_date
    else:
        # Default to today
        start = datetime(now.year, now.month, now.day, 0, 0, 0)
        end = datetime(now.year, now.month, now.day, 23, 59, 59)

    logger.info(f"Date range for '{range_type}': {start} to {end}")
    return start, end


def get_historical_deals(from_date: datetime, to_date: datetime, magic: int = 2025) -> List:
    """
    Fetch historical deals from MT5 for a given date range

    Args:
        from_date: Start date
        to_date: End date
        magic: Magic number filter (default 2025)

    Returns:
        List of deal objects
    """
    try:
        deals = mt5.history_deals_get(from_date, to_date)
        if deals is None or len(deals) == 0:
            logger.info(f"No deals found for range {from_date} to {to_date}")
            return []

        # Filter by magic number if needed
        filtered_deals = [deal for deal in deals if deal.magic == magic]
        logger.info(f"Found {len(filtered_deals)} deals with magic {magic} in date range")
        return filtered_deals
    except Exception as e:
        logger.error(f"Error fetching historical deals: {e}")
        return []


def get_historical_orders(from_date: datetime, to_date: datetime, magic: int = 2025) -> List:
    """
    Fetch historical orders from MT5 for a given date range

    Args:
        from_date: Start date
        to_date: End date
        magic: Magic number filter (default 2025)

    Returns:
        List of order objects
    """
    try:
        orders = mt5.history_orders_get(from_date, to_date)
        if orders is None or len(orders) == 0:
            logger.info(f"No orders found for range {from_date} to {to_date}")
            return []

        # Filter by magic number
        filtered_orders = [order for order in orders if order.magic == magic]
        logger.info(f"Found {len(filtered_orders)} orders with magic {magic} in date range")
        return filtered_orders
    except Exception as e:
        logger.error(f"Error fetching historical orders: {e}")
        return []


def group_deals_by_position(deals: List) -> Dict[int, List]:
    """
    Group MT5 deals by their position_id (canonical identifier).

    IMPORTANT: position_id is the persistent identifier that remains constant
    throughout a position's lifecycle. Deal tickets change for each event
    (entry, partial close, exit), but position_id stays the same.

    Example:
        Position 12345 might have deals:
        - Deal 67890 (ENTRY): position_id=12345
        - Deal 67891 (OUT): position_id=12345
        All grouped under position_id=12345

    Args:
        deals: List of MT5 deal objects from history_deals_get()

    Returns:
        Dictionary mapping position_id (int) to list of deals for that position
    """
    grouped = {}
    for deal in deals:
        # Extract position_id from deal (the canonical identifier)
        position_id = deal.position_id if hasattr(deal, 'position_id') else deal.position
        if position_id not in grouped:
            grouped[position_id] = []
        grouped[position_id].append(deal)
    return grouped


def calculate_position_metrics(deals: List, signal_data: Dict = None) -> Dict:
    """
    Calculate comprehensive metrics for a position based on its deals

    Args:
        deals: List of deals for this position (sorted by time)
        signal_data: Optional signal data for additional context

    Returns:
        Dictionary with calculated metrics
    """
    if not deals:
        return {}

    # Sort deals by time
    sorted_deals = sorted(deals, key=lambda d: d.time)

    # First deal is entry, last deal is exit
    entry_deal = sorted_deals[0]
    exit_deal = sorted_deals[-1] if len(sorted_deals) > 1 else entry_deal

    # Calculate P&L
    total_profit = sum(deal.profit for deal in sorted_deals)
    total_commission = sum(deal.commission for deal in sorted_deals)
    total_swap = sum(deal.swap for deal in sorted_deals)
    net_profit = total_profit + total_commission + total_swap

    # Calculate volume
    total_volume = sum(deal.volume for deal in sorted_deals if deal.entry == 0)  # Entry deals only

    # Calculate time in trade
    if len(sorted_deals) > 1:
        time_in_trade_seconds = exit_deal.time - entry_deal.time
        time_in_trade = timedelta(seconds=time_in_trade_seconds)
    else:
        time_in_trade = timedelta(0)

    # Get entry and exit prices
    entry_price = entry_deal.price
    exit_price = exit_deal.price if len(sorted_deals) > 1 else entry_price

    # Determine position type (BUY/SELL)
    position_type = "BUY" if entry_deal.type == 0 else "SELL"

    # Calculate price movement
    if position_type == "BUY":
        price_change = exit_price - entry_price
    else:
        price_change = entry_price - exit_price

    # Calculate ROI (return on investment)
    # ROI = (Net Profit / Required Margin) * 100
    # Approximate required margin based on volume and price
    roi_percent = 0
    if signal_data:
        entry_price_signal = signal_data.get('open_price', entry_price)
        # Rough estimate: margin = volume * contract_size * price / leverage
        # For simplicity, we'll use profit percent relative to entry value
        entry_value = total_volume * entry_price * 100000  # Assuming forex, contract size 100k
        if entry_value > 0:
            roi_percent = (net_profit / entry_value) * 100

    # Determine exit reason
    exit_reason = "UNKNOWN"
    if signal_data and len(sorted_deals) > 1:  # Must have actually closed
        sl = signal_data.get('stop_loss')
        tp_list = signal_data.get('tp_list', [])

        # Convert SL to float if it's a string or None
        if sl and sl != 0 and sl != "0":
            try:
                sl = float(sl)
            except:
                sl = None
        else:
            sl = None

        # Parse TP list if it's a string
        if tp_list and isinstance(tp_list, str):
            try:
                tp_list = [float(x.strip()) for x in tp_list.split(',') if x.strip()]
            except:
                tp_list = []
        elif not tp_list or not isinstance(tp_list, list):
            tp_list = []

        if sl or tp_list:

            # Use a more flexible threshold based on symbol (accounting for slippage)
            # Thresholds are generous to account for market slippage
            symbol = entry_deal.symbol.upper()
            if 'XAU' in symbol or 'GOLD' in symbol:
                threshold = 2.0  # $2 for gold (accounts for slippage)
            elif 'XAG' in symbol or 'SILVER' in symbol:
                threshold = 0.10  # 10 cents for silver
            elif 'JPY' in symbol:
                threshold = 0.10  # 10 pips for JPY pairs
            else:
                threshold = 0.0010  # 10 pips for other forex pairs

            # Check SL first (sl is already converted to float or None)
            if sl:
                if abs(exit_price - sl) <= threshold:
                    exit_reason = "STOP_LOSS"

            # If not SL, check TP levels
            if exit_reason == "UNKNOWN" and tp_list:
                for idx, tp in enumerate(tp_list, 1):
                    try:
                        tp_float = float(tp)
                        if abs(exit_price - tp_float) <= threshold:
                            exit_reason = f"TP{idx}"
                            break
                    except:
                        continue

            # If still unknown, it's a manual close
            if exit_reason == "UNKNOWN":
                exit_reason = "MANUAL_CLOSE"
    elif len(sorted_deals) == 1:
        exit_reason = "STILL_OPEN"

    # Calculate maximum drawdown (approximate - we don't have tick data)
    # This is a simplified calculation
    max_drawdown = 0
    max_drawdown_percent = 0

    # Build comprehensive metrics dictionary
    metrics = {
        'position_id': entry_deal.position_id if hasattr(entry_deal, 'position_id') else entry_deal.position,
        'symbol': entry_deal.symbol,
        'position_type': position_type,
        'entry_price': entry_price,
        'exit_price': exit_price,
        'volume': total_volume,
        'entry_time': datetime.fromtimestamp(entry_deal.time),
        'exit_time': datetime.fromtimestamp(exit_deal.time) if len(sorted_deals) > 1 else None,
        'time_in_trade': time_in_trade,
        'time_in_trade_str': format_timedelta(time_in_trade),
        'profit': total_profit,
        'commission': total_commission,
        'swap': total_swap,
        'net_profit': net_profit,
        'roi_percent': roi_percent,
        'exit_reason': exit_reason,
        'price_change': price_change,
        'max_drawdown': max_drawdown,
        'max_drawdown_percent': max_drawdown_percent,
        'num_deals': len(sorted_deals)
    }

    return metrics


def format_timedelta(td: timedelta) -> str:
    """Format timedelta as human-readable string"""
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if not parts:  # If less than a minute
        parts.append(f"{seconds}s")

    return " ".join(parts)


def match_positions_with_signals(deals: List) -> List[Dict]:
    """
    Match historical deals with signals from database

    CRITICAL: This function groups MT5 deals by their position_id (the canonical identifier).
    The position_id is persistent throughout a position's lifecycle.

    IMPORTANT: If signals are not being found, the issue is likely that the database
    contains deal/order ticket numbers instead of position_ids. See mt5_position_tracker.py
    for correct position_id extraction.

    Args:
        deals: List of deal objects from mt5.history_deals_get()

    Returns:
        List of dictionaries with position metrics and signal data
    """
    try:
        # Group deals by position_id (not deal ticket!)
        grouped_deals = group_deals_by_position(deals)
        logger.info(f"[MATCH_SIGNALS] Grouped {len(deals)} deals into {len(grouped_deals)} positions")

        signal_repo = db_manager.get_signal_repository()
        position_repo = db_manager.get_position_repository()

        results = []
        signals_found = 0
        signals_not_found = 0
        mismatched_tickets = []

        for position_id, position_deals in grouped_deals.items():
            # Try to find signal for this position using direct method (JOIN query)
            signal = signal_repo.get_signal_by_position_id(position_id)

            signal_data = None
            if signal:
                signals_found += 1
                # SignalModel object - access attributes directly
                signal_data = {
                    'signal_id': signal.id,
                    'provider': signal.provider if signal.provider else 'telegram',
                    'channel': signal.telegram_channel_title,
                    'message_id': signal.telegram_message_id,
                    'chat_id': signal.telegram_message_chatid,
                    'signal_type': signal.signal_type,
                    'open_price': signal.open_price,
                    'stop_loss': signal.stop_loss,
                    'tp_list': signal.tp_list,
                    'symbol': signal.symbol
                }
            else:
                signals_not_found += 1

                # DIAGNOSTIC: Try to find if any of the deal tickets are in the database (only for first few)
                if len(mismatched_tickets) < 3:  # Only check first 3 to avoid spam
                    deal_tickets = [d.ticket for d in position_deals]
                    for deal_ticket in deal_tickets:
                        try:
                            diagnostic_query = position_repo.get_position_by_ticket(deal_ticket)
                            if diagnostic_query:
                                mismatched_tickets.append({
                                    'db_stored': deal_ticket,
                                    'correct_position_id': position_id
                                })
                                break
                        except:
                            pass

            # Calculate metrics
            metrics = calculate_position_metrics(position_deals, signal_data)

            # Combine metrics and signal data
            result = {
                'metrics': metrics,
                'signal': signal_data,
                'has_signal': signal_data is not None
            }

            results.append(result)

        # Summary logging
        logger.info(f"[MATCH_SIGNALS] Summary: {len(grouped_deals)} positions | {signals_found} with signals | {signals_not_found} without signals")

        # Only log detailed diagnostic if there are mismatches
        if mismatched_tickets:
            logger.error(f"[MATCH_SIGNALS] ⚠️ DIAGNOSIS: Database contains DEAL TICKETS instead of POSITION IDs!")
            for mismatch in mismatched_tickets:
                logger.error(f"[MATCH_SIGNALS]   - DB has: {mismatch['db_stored']} (deal ticket) | Should be: {mismatch['correct_position_id']} (position_id)")
            logger.error(f"[MATCH_SIGNALS] ⚠️ FIX: Update trade creation code to store result.order (position_id) not result.deal (deal ticket)")
            logger.error(f"[MATCH_SIGNALS] ⚠️ See CRITICAL_FIX_POSITION_ID.md for details")

        # Sort by entry time (newest first)
        results.sort(key=lambda x: x['metrics']['entry_time'], reverse=True)

        return results

    except Exception as e:
        logger.error(f"[MATCH_SIGNALS] Error matching positions with signals: {e}", exc_info=True)
        return []


def get_open_positions_with_metrics(meta_trader) -> List[Dict]:
    """
    Get currently open positions with calculated metrics

    Args:
        meta_trader: MetaTrader instance

    Returns:
        List of dictionaries with position metrics and signal data
    """
    try:
        if not meta_trader:
            return []

        positions = meta_trader.get_open_positions() or []
        signal_repo = db_manager.get_signal_repository()

        results = []

        for pos in positions:
            ticket = pos.ticket if hasattr(pos, 'ticket') else pos.get('ticket')

            # Find signal for this position using direct method (JOIN query)
            signal = signal_repo.get_signal_by_position_id(ticket)

            signal_data = None
            if signal:
                # SignalModel object - access attributes directly
                signal_data = {
                    'signal_id': signal.id,
                    'provider': signal.provider if signal.provider else 'telegram',
                    'channel': signal.telegram_channel_title,
                    'message_id': signal.telegram_message_id,
                    'chat_id': signal.telegram_message_chatid,
                    'signal_type': signal.signal_type,
                    'open_price': signal.open_price,
                    'stop_loss': signal.stop_loss,
                    'tp_list': signal.tp_list,
                    'symbol': signal.symbol
                }

            # Calculate metrics for open position
            entry_price = pos.price_open if hasattr(pos, 'price_open') else pos.get('price_open', 0)
            current_price = pos.price_current if hasattr(pos, 'price_current') else pos.get('price_current', 0)
            profit = pos.profit if hasattr(pos, 'profit') else pos.get('profit', 0)
            volume = pos.volume if hasattr(pos, 'volume') else pos.get('volume', 0)
            position_type = "BUY" if pos.type == 0 else "SELL"

            # Calculate time in trade
            open_time = pos.time if hasattr(pos, 'time') else pos.get('time', 0)
            time_in_trade = datetime.now() - datetime.fromtimestamp(open_time)

            # Calculate approximate ROI
            roi_percent = 0
            if signal_data:
                entry_value = volume * entry_price * 100000
                if entry_value > 0:
                    roi_percent = (profit / entry_value) * 100

            # Calculate current drawdown/gain
            if position_type == "BUY":
                price_change = current_price - entry_price
            else:
                price_change = entry_price - current_price

            metrics = {
                'position_id': ticket,
                'symbol': pos.symbol if hasattr(pos, 'symbol') else pos.get('symbol'),
                'position_type': position_type,
                'entry_price': entry_price,
                'current_price': current_price,
                'volume': volume,
                'entry_time': datetime.fromtimestamp(open_time),
                'time_in_trade': time_in_trade,
                'time_in_trade_str': format_timedelta(time_in_trade),
                'profit': profit,
                'net_profit': profit,
                'roi_percent': roi_percent,
                'exit_reason': 'OPEN',
                'price_change': price_change,
                'is_open': True
            }

            result = {
                'metrics': metrics,
                'signal': signal_data,
                'has_signal': signal_data is not None
            }

            results.append(result)

        return results

    except Exception as e:
        logger.error(f"Error getting open positions with metrics: {e}")
        return []
