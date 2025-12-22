"""
Quick diagnostic script to check what positions are linked to each channel in the database
"""

import sqlite3
from pathlib import Path

# Database path
db_path = Path(__file__).parent / "app" / "signaltrader.db"

print("=" * 80)
print("DATABASE DIAGNOSTIC: Channel -> Position Mapping")
print("=" * 80)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query to show all channels
    print("\n1. ALL CHANNELS IN DATABASE:")
    print("-" * 80)
    cursor.execute("""
        SELECT DISTINCT telegram_channel_title, provider
        FROM Signals
        WHERE telegram_channel_title IS NOT NULL
        ORDER BY telegram_channel_title
    """)
    channels = cursor.fetchall()
    for idx, (channel, provider) in enumerate(channels, 1):
        print(f"   {idx}. {channel} (Provider: {provider})")

    # For each channel, show linked positions
    print("\n2. POSITIONS LINKED TO EACH CHANNEL:")
    print("-" * 80)
    for channel, provider in channels:
        cursor.execute("""
            SELECT p.position_id, p.signal_id, s.telegram_channel_title
            FROM Positions p
            INNER JOIN Signals s ON p.signal_id = s.id
            WHERE s.telegram_channel_title = ?
            ORDER BY p.position_id DESC
        """, (channel,))

        positions = cursor.fetchall()
        print(f"\nChannel: '{channel}'")
        print(f"  Found {len(positions)} position(s):")
        for pos_id, sig_id, ch_name in positions:
            print(f"    - Position ID: {pos_id} (Signal ID: {sig_id})")

    # Check for duplicate position_ids across channels
    print("\n3. CHECKING FOR DUPLICATES:")
    print("-" * 80)
    cursor.execute("""
        SELECT p.position_id, COUNT(DISTINCT s.telegram_channel_title) as channel_count,
               GROUP_CONCAT(DISTINCT s.telegram_channel_title) as channels
        FROM Positions p
        INNER JOIN Signals s ON p.signal_id = s.id
        WHERE s.telegram_channel_title IS NOT NULL
        GROUP BY p.position_id
        HAVING channel_count > 1
    """)

    duplicates = cursor.fetchall()
    if duplicates:
        print("  ⚠️  FOUND DUPLICATE POSITION IDs ACROSS CHANNELS:")
        for pos_id, count, channels_str in duplicates:
            print(f"    Position {pos_id} is linked to {count} channels: {channels_str}")
            print(f"    ⚠️  This is why all channels show the same data!")
    else:
        print("  ✅ No duplicate position_ids found. Each position is linked to only one channel.")

    # Show signal details for each position
    print("\n4. DETAILED SIGNAL INFO:")
    print("-" * 80)
    cursor.execute("""
        SELECT
            p.position_id,
            s.id as signal_id,
            s.telegram_channel_title,
            s.symbol,
            s.signal_type,
            s.provider
        FROM Positions p
        INNER JOIN Signals s ON p.signal_id = s.id
        ORDER BY s.telegram_channel_title, p.position_id
    """)

    all_positions = cursor.fetchall()
    current_channel = None
    for pos_id, sig_id, channel, symbol, sig_type, provider in all_positions:
        if channel != current_channel:
            print(f"\n  Channel: '{channel}'")
            current_channel = channel
        print(f"    Position {pos_id}: Signal #{sig_id} - {sig_type} {symbol}")

    conn.close()

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
