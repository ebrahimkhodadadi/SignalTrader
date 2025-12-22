"""
MT5 Position ID Tracking - Best Practices

CRITICAL: Understanding MT5 Position vs Deal vs Order
=====================================================

MT5 uses three different identifiers:
1. ORDER TICKET: Temporary ID when order is placed (not persistent)
2. DEAL TICKET: ID for each execution event (entry, exit, partial close)
3. POSITION ID: The canonical, persistent identifier for a position's lifecycle

CORRECT APPROACH:
- Store position_id in database (from result.order after order_send)
- Query using position_id for both open and closed positions
- Deal tickets are ephemeral and should NOT be used as primary keys

This module provides helper functions to correctly extract and track position IDs.
"""

from typing import Optional, Dict, Any
from loguru import logger
import MetaTrader5 as mt5


def extract_position_id_from_trade_result(result) -> Optional[int]:
    """
    Extract position_id from MT5 trade result after order_send.

    Args:
        result: MT5 trade result object from order_send

    Returns:
        position_id (int) if found, None otherwise

    Usage:
        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            position_id = extract_position_id_from_trade_result(result)
            # Store position_id in database, NOT result.deal or result.order
    """
    if not result:
        logger.error("[MT5_TRACKER] Trade result is None")
        return None

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.warning(f"[MT5_TRACKER] Trade not successful: {result.retcode}")
        return None

    # result.order contains the position_id for market orders
    position_id = result.order

    logger.info(f"[MT5_TRACKER] Extracted position_id: {position_id}")
    logger.debug(f"[MT5_TRACKER] Trade result details - order: {result.order}, deal: {result.deal}, volume: {result.volume}")

    # IMPORTANT: result.deal is the DEAL TICKET, not the position ID
    if result.deal != position_id:
        logger.warning(f"[MT5_TRACKER] Deal ticket ({result.deal}) != position_id ({position_id}) - this is normal")

    return position_id


def verify_position_exists(position_id: int) -> Optional[Dict[str, Any]]:
    """
    Check if a position is still open in MT5.

    Args:
        position_id: The MT5 position ID to check

    Returns:
        Position data dict if open, None if closed
    """
    if not position_id:
        return None

    try:
        positions = mt5.positions_get(ticket=position_id)

        if positions and len(positions) > 0:
            pos = positions[0]
            logger.info(f"[MT5_TRACKER] Position {position_id} is OPEN - Symbol: {pos.symbol}, Profit: {pos.profit}")
            return {
                'position_id': pos.ticket,
                'symbol': pos.symbol,
                'type': pos.type,
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'profit': pos.profit,
                'sl': pos.sl,
                'tp': pos.tp,
                'time': pos.time
            }
        else:
            logger.info(f"[MT5_TRACKER] Position {position_id} is CLOSED or not found")
            return None

    except Exception as e:
        logger.error(f"[MT5_TRACKER] Error checking position {position_id}: {e}")
        return None


def get_closed_position_from_history(position_id: int, days_back: int = 30) -> Optional[Dict[str, Any]]:
    """
    Find closed position data from MT5 history using position_id.

    Args:
        position_id: The MT5 position ID to find
        days_back: How many days back to search (default 30)

    Returns:
        Dict with exit deal information if found, None otherwise
    """
    from datetime import datetime, timedelta

    if not position_id:
        logger.error("[MT5_TRACKER] position_id is None")
        return None

    try:
        # Search history
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days_back)

        logger.info(f"[MT5_TRACKER] Searching history for position_id {position_id} from {from_date} to {to_date}")

        deals = mt5.history_deals_get(from_date, to_date)
        if not deals:
            logger.warning(f"[MT5_TRACKER] No deals found in history")
            return None

        # Find the DEAL_ENTRY_OUT deal for this position
        exit_deal = None
        entry_deal = None

        for deal in deals:
            if hasattr(deal, 'position_id'):
                deal_position_id = deal.position_id
            elif hasattr(deal, 'position'):
                deal_position_id = deal.position
            else:
                continue

            if deal_position_id == position_id:
                if deal.entry == mt5.DEAL_ENTRY_OUT:
                    exit_deal = deal
                    logger.info(f"[MT5_TRACKER] Found EXIT deal for position {position_id} - Deal ticket: {deal.ticket}, Price: {deal.price}, Profit: {deal.profit}")
                elif deal.entry == mt5.DEAL_ENTRY_IN:
                    entry_deal = deal
                    logger.info(f"[MT5_TRACKER] Found ENTRY deal for position {position_id} - Deal ticket: {deal.ticket}, Price: {deal.price}")

        if exit_deal:
            return {
                'position_id': position_id,
                'exit_deal_ticket': exit_deal.ticket,
                'entry_deal_ticket': entry_deal.ticket if entry_deal else None,
                'symbol': exit_deal.symbol,
                'type': exit_deal.type,
                'volume': exit_deal.volume,
                'entry_price': entry_deal.price if entry_deal else None,
                'exit_price': exit_deal.price,
                'profit': exit_deal.profit,
                'entry_time': entry_deal.time if entry_deal else None,
                'exit_time': exit_deal.time
            }
        else:
            logger.warning(f"[MT5_TRACKER] No exit deal found for position {position_id}")
            return None

    except Exception as e:
        logger.error(f"[MT5_TRACKER] Error getting closed position {position_id}: {e}", exc_info=True)
        return None


def get_position_lifecycle_info(position_id: int) -> Dict[str, Any]:
    """
    Get complete lifecycle information for a position.

    Returns state (OPEN/CLOSED/NOT_FOUND) and all available data.

    Args:
        position_id: The MT5 position ID

    Returns:
        Dict with 'state' and 'data' keys
    """
    logger.info(f"[MT5_TRACKER] Getting lifecycle info for position_id: {position_id}")

    # First check if position is still open
    open_data = verify_position_exists(position_id)
    if open_data:
        return {
            'state': 'OPEN',
            'position_id': position_id,
            'data': open_data
        }

    # If not open, check history
    closed_data = get_closed_position_from_history(position_id)
    if closed_data:
        return {
            'state': 'CLOSED',
            'position_id': position_id,
            'data': closed_data
        }

    # Not found anywhere
    logger.warning(f"[MT5_TRACKER] Position {position_id} not found in open positions or history")
    return {
        'state': 'NOT_FOUND',
        'position_id': position_id,
        'data': None
    }


def validate_database_position_ids(db_manager) -> Dict[str, Any]:
    """
    Diagnostic function to validate all position_ids in database.

    Checks if stored position_ids are valid MT5 position IDs or if they're
    actually deal/order tickets (which would be incorrect).

    Args:
        db_manager: Database manager instance

    Returns:
        Dict with validation results and recommendations
    """
    logger.info("[MT5_TRACKER] Starting database position_id validation...")

    try:
        position_repo = db_manager.get_position_repository()
        all_positions = position_repo.get_all_positions()

        results = {
            'total_positions': len(all_positions),
            'valid_ids': 0,
            'invalid_ids': 0,
            'not_found': 0,
            'issues': []
        }

        for db_pos in all_positions[:10]:  # Check first 10 for sample
            position_id = db_pos.position_id if hasattr(db_pos, 'position_id') else db_pos.get('position_id')

            lifecycle = get_position_lifecycle_info(position_id)

            if lifecycle['state'] in ['OPEN', 'CLOSED']:
                results['valid_ids'] += 1
            elif lifecycle['state'] == 'NOT_FOUND':
                results['not_found'] += 1
                results['issues'].append({
                    'db_id': db_pos.id if hasattr(db_pos, 'id') else db_pos.get('id'),
                    'stored_position_id': position_id,
                    'signal_id': db_pos.signal_id if hasattr(db_pos, 'signal_id') else db_pos.get('signal_id'),
                    'issue': 'Position ID not found in MT5 - may be deal/order ticket instead of position_id'
                })

        logger.info(f"[MT5_TRACKER] Validation complete: {results['valid_ids']} valid, {results['not_found']} not found")

        if results['not_found'] > 0:
            logger.warning(f"[MT5_TRACKER] Found {results['not_found']} positions with invalid IDs - these may be deal tickets instead of position IDs")

        return results

    except Exception as e:
        logger.error(f"[MT5_TRACKER] Error during validation: {e}", exc_info=True)
        return {'error': str(e)}
