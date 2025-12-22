"""
Diagnostic Script: Position ID vs Deal Ticket Issue
=====================================================

Run this script to diagnose if the database is storing deal tickets
instead of position IDs.

This will:
1. Fetch recent closed deals from MT5
2. Show what position_id MT5 reports
3. Check what's stored in the database
4. Identify mismatches
"""

import sys
from datetime import datetime, timedelta
from loguru import logger
import MetaTrader5 as mt5

# Configure logger
logger.remove()
logger.add(sys.stdout, level="INFO")

def diagnose():
    """Run comprehensive diagnostic"""

    print("=" * 80)
    print("DIAGNOSTIC: Position ID vs Deal Ticket Analysis")
    print("=" * 80)

    # Initialize MT5
    if not mt5.initialize():
        print("❌ Failed to initialize MT5")
        return

    print("\n✓ MT5 initialized")

    # Import database manager
    try:
        from Database.database_manager import db_manager
        print("✓ Database manager loaded")
    except Exception as e:
        print(f"❌ Failed to load database manager: {e}")
        return

    # Get recent deals
    print("\n" + "=" * 80)
    print("STEP 1: Fetching recent MT5 deals...")
    print("=" * 80)

    to_date = datetime.now()
    from_date = to_date - timedelta(days=7)

    deals = mt5.history_deals_get(from_date, to_date)
    if not deals:
        print("❌ No deals found in last 7 days")
        mt5.shutdown()
        return

    print(f"✓ Found {len(deals)} deals in last 7 days")

    # Group by position
    positions_data = {}
    for deal in deals:
        position_id = deal.position_id if hasattr(deal, 'position_id') else deal.position
        if position_id not in positions_data:
            positions_data[position_id] = {
                'position_id': position_id,
                'deals': [],
                'symbol': deal.symbol
            }
        positions_data[position_id]['deals'].append({
            'ticket': deal.ticket,
            'type': 'IN' if deal.entry == 0 else 'OUT',
            'time': datetime.fromtimestamp(deal.time)
        })

    print(f"✓ Grouped into {len(positions_data)} unique positions")

    # Analyze each position
    print("\n" + "=" * 80)
    print("STEP 2: Analyzing Position IDs vs Deal Tickets...")
    print("=" * 80)

    signal_repo = db_manager.get_signal_repository()
    position_repo = db_manager.get_position_repository()

    issues_found = 0
    total_checked = 0

    for idx, (position_id, data) in enumerate(positions_data.items(), 1):
        if idx > 10:  # Check first 10
            print(f"\n... (checking first 10 of {len(positions_data)} positions)")
            break

        total_checked += 1

        print(f"\n--- Position {idx} ---")
        print(f"MT5 Position ID: {position_id}")
        print(f"Symbol: {data['symbol']}")
        print(f"Deals:")
        for deal in data['deals']:
            print(f"  - Deal Ticket: {deal['ticket']} ({deal['type']}) at {deal['time']}")

        # Check if this position_id exists in database
        print(f"\nQuerying database for position_id={position_id}...")
        signal = signal_repo.get_signal_by_position_id(position_id)

        if signal:
            print(f"✓ FOUND in database! Signal ID: {signal.id}")
        else:
            print(f"✗ NOT FOUND in database with position_id={position_id}")
            issues_found += 1

            # Check if any of the deal tickets are in the database
            print(f"\nDiagnostic: Checking if deal tickets are in database instead...")
            for deal in data['deals']:
                deal_ticket = deal['ticket']
                try:
                    db_pos = position_repo.get_position_by_ticket(deal_ticket)
                    if db_pos:
                        print(f"⚠️  FOUND IT! Deal ticket {deal_ticket} is stored as position_id in database!")
                        print(f"⚠️  This is INCORRECT. Should be {position_id} instead.")
                        issues_found += 1

                        # Get the signal to show what's linked
                        signal_id = db_pos.signal_id if hasattr(db_pos, 'signal_id') else db_pos.get('signal_id')
                        signal = signal_repo.get_signal_by_id(signal_id)
                        if signal:
                            print(f"⚠️  This is linked to Signal #{signal_id}: {signal.symbol} {signal.signal_type}")
                        break
                except:
                    pass

    # Summary
    print("\n" + "=" * 80)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 80)
    print(f"Total positions checked: {total_checked}")
    print(f"Issues found: {issues_found}")

    if issues_found > 0:
        print("\n⚠️  PROBLEM IDENTIFIED:")
        print("   Database is storing DEAL TICKETS instead of POSITION IDs")
        print("\n📋 SOLUTION:")
        print("   1. Read CRITICAL_FIX_POSITION_ID.md for detailed fix instructions")
        print("   2. Update trade creation code to store result.order (position_id)")
        print("   3. Ensure you're NOT storing result.deal (deal ticket)")
        print("\n🔍 WHERE TO FIX:")
        print("   - Find code that calls mt5.order_send()")
        print("   - Look for position_repo.insert() or similar")
        print("   - Change: position_id = result.deal  ❌")
        print("   - To:     position_id = result.order ✅")
    else:
        print("\n✓ No issues found! Position IDs are stored correctly.")

    mt5.shutdown()

    print("\n" + "=" * 80)
    print("Diagnostic complete. See logs above for details.")
    print("=" * 80)


if __name__ == "__main__":
    try:
        diagnose()
    except Exception as e:
        logger.error(f"Diagnostic failed with error: {e}", exc_info=True)
        print(f"\n❌ Diagnostic failed: {e}")
