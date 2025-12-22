"""
Channel Performance Analyzer
Analyzes trading performance by signal provider channel
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from loguru import logger
import MetaTrader5 as mt5


@dataclass
class ChannelStats:
    """Statistics for a single channel"""
    channel_name: str
    provider: str
    chat_id: Optional[str] = None

    # Position counts
    total_positions: int = 0
    open_positions: int = 0
    closed_positions: int = 0
    winning_positions: int = 0
    losing_positions: int = 0

    # Financial metrics
    total_profit: float = 0.0
    total_loss: float = 0.0
    net_profit: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0

    # Performance metrics
    win_rate: float = 0.0
    profit_factor: float = 0.0
    average_roi: float = 0.0

    # Risk metrics
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0

    # Volume
    total_volume: float = 0.0

    # Time periods
    first_trade_date: Optional[datetime] = None
    last_trade_date: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'channel_name': self.channel_name,
            'provider': self.provider,
            'chat_id': self.chat_id,
            'total_positions': self.total_positions,
            'open_positions': self.open_positions,
            'closed_positions': self.closed_positions,
            'winning_positions': self.winning_positions,
            'losing_positions': self.losing_positions,
            'total_profit': round(self.total_profit, 2),
            'total_loss': round(self.total_loss, 2),
            'net_profit': round(self.net_profit, 2),
            'largest_win': round(self.largest_win, 2),
            'largest_loss': round(self.largest_loss, 2),
            'average_win': round(self.average_win, 2),
            'average_loss': round(self.average_loss, 2),
            'win_rate': round(self.win_rate, 2),
            'profit_factor': round(self.profit_factor, 2),
            'average_roi': round(self.average_roi, 2),
            'max_drawdown': round(self.max_drawdown, 2),
            'current_drawdown': round(self.current_drawdown, 2),
            'total_volume': round(self.total_volume, 2),
            'first_trade_date': self.first_trade_date.isoformat() if self.first_trade_date else None,
            'last_trade_date': self.last_trade_date.isoformat() if self.last_trade_date else None,
        }


class ChannelAnalyzer:
    """Analyzes trading performance by channel"""

    def __init__(self, db_manager):
        """
        Initialize the analyzer

        Args:
            db_manager: Database manager instance
        """
        self.db_manager = db_manager
        self.logger = logger

    def get_all_channels(self) -> List[Dict[str, str]]:
        """
        Get list of all unique channels with signals

        Returns:
            List of dicts with channel info: {channel_name, provider, chat_id}
        """
        try:
            signal_repo = self.db_manager.get_signal_repository()
            channels = signal_repo.get_distinct_channels()
            self.logger.info(f"Found {len(channels)} unique channels")
            return channels
        except Exception as e:
            self.logger.error(f"Error fetching channels: {e}", exc_info=True)
            return []

    def analyze_channel(
        self,
        channel_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ChannelStats:
        """
        Analyze performance for a specific channel by fetching data from MT5

        Args:
            channel_name: Name of the channel to analyze
            start_date: Optional start date for analysis period
            end_date: Optional end date for analysis period

        Returns:
            ChannelStats object with comprehensive statistics
        """
        try:
            signal_repo = self.db_manager.get_signal_repository()

            # Get position IDs for this channel from database
            position_ids = signal_repo.get_position_ids_by_channel(channel_name)

            # Debug logging
            self.logger.info(f"[ANALYZE] Channel '{channel_name}' has position_ids: {position_ids}")

            if not position_ids:
                self.logger.warning(f"No positions found for channel: {channel_name}")
                return ChannelStats(channel_name=channel_name, provider="telegram")

            # Initialize stats
            stats = ChannelStats(
                channel_name=channel_name,
                provider="telegram"
            )

            # Process each position by fetching from MT5
            all_pnl = []

            for position_id in position_ids:
                # Try to get from open positions first
                position_data = self._get_position_from_mt5(position_id, start_date, end_date)

                if not position_data:
                    self.logger.warning(f"[ANALYZE] Channel '{channel_name}': Position {position_id} - No data from MT5")
                    continue

                self.logger.info(f"[ANALYZE] Channel '{channel_name}': Position {position_id} - "
                               f"Profit: {position_data.get('profit', 0.0):.2f}, "
                               f"Commission: {position_data.get('commission', 0.0):.2f}, "
                               f"Swap: {position_data.get('swap', 0.0):.2f}, "
                               f"Volume: {position_data.get('volume', 0.0):.2f}, "
                               f"Open: {position_data['is_open']}")

                stats.total_positions += 1
                is_open = position_data['is_open']

                if is_open:
                    stats.open_positions += 1
                else:
                    stats.closed_positions += 1

                # Get metrics
                profit = position_data.get('profit', 0.0)
                commission = position_data.get('commission', 0.0)
                swap = position_data.get('swap', 0.0)
                net_profit = profit - commission - swap
                volume = position_data.get('volume', 0.0)

                stats.total_volume += volume

                # Only process closed positions for P&L stats
                if not is_open:
                    all_pnl.append(net_profit)
                    self.logger.info(f"[ANALYZE] Channel '{channel_name}': Position {position_id} - Net P&L: ${net_profit:.2f}")

                    if net_profit > 0:
                        stats.winning_positions += 1
                        stats.total_profit += net_profit
                        if net_profit > stats.largest_win:
                            stats.largest_win = net_profit
                    elif net_profit < 0:
                        stats.losing_positions += 1
                        stats.total_loss += abs(net_profit)
                        if net_profit < stats.largest_loss:
                            stats.largest_loss = net_profit

                # Track dates
                entry_time = position_data.get('entry_time')
                if entry_time:
                    if stats.first_trade_date is None or entry_time < stats.first_trade_date:
                        stats.first_trade_date = entry_time
                    if stats.last_trade_date is None or entry_time > stats.last_trade_date:
                        stats.last_trade_date = entry_time

            # Calculate derived metrics
            stats.net_profit = stats.total_profit - stats.total_loss

            if stats.closed_positions > 0:
                stats.win_rate = (stats.winning_positions / stats.closed_positions) * 100

            if stats.winning_positions > 0:
                stats.average_win = stats.total_profit / stats.winning_positions

            if stats.losing_positions > 0:
                stats.average_loss = stats.total_loss / stats.losing_positions

            if stats.total_loss > 0:
                stats.profit_factor = stats.total_profit / stats.total_loss

            # Calculate drawdown
            if all_pnl:
                stats.max_drawdown = self._calculate_max_drawdown(all_pnl)
                stats.current_drawdown = self._calculate_current_drawdown(all_pnl)

            self.logger.info(
                f"[ANALYZE] ===== FINAL STATS for Channel '{channel_name}' ====="
            )
            self.logger.info(
                f"[ANALYZE] Total Positions: {stats.total_positions} "
                f"(Open: {stats.open_positions}, Closed: {stats.closed_positions})"
            )
            self.logger.info(
                f"[ANALYZE] Winning: {stats.winning_positions}, Losing: {stats.losing_positions}"
            )
            self.logger.info(
                f"[ANALYZE] Total Profit: ${stats.total_profit:.2f}, Total Loss: ${stats.total_loss:.2f}"
            )
            self.logger.info(
                f"[ANALYZE] Net P&L: ${stats.net_profit:.2f}, Win Rate: {stats.win_rate:.1f}%"
            )
            self.logger.info(
                f"[ANALYZE] Largest Win: ${stats.largest_win:.2f}, Largest Loss: ${stats.largest_loss:.2f}"
            )
            self.logger.info(f"[ANALYZE] ==================================================")

            return stats

        except Exception as e:
            self.logger.error(f"Error analyzing channel {channel_name}: {e}", exc_info=True)
            return ChannelStats(channel_name=channel_name, provider="telegram")

    def _get_position_from_mt5(
        self,
        position_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[Dict]:
        """
        Fetch position data from MT5 (either open position or history)

        Args:
            position_id: The MT5 position ID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with position data or None if not found
        """
        try:
            # First check if position is still open
            open_positions = mt5.positions_get(ticket=position_id)
            if open_positions and len(open_positions) > 0:
                pos = open_positions[0]
                entry_time = datetime.fromtimestamp(pos.time)

                # Check date filter
                if start_date and entry_time < start_date:
                    return None
                if end_date and entry_time > end_date:
                    return None

                return {
                    'position_id': pos.ticket,
                    'symbol': pos.symbol,
                    'volume': pos.volume,
                    'entry_price': pos.price_open,
                    'current_price': pos.price_current,
                    'profit': pos.profit,
                    'commission': 0.0,  # Open positions don't have commission yet
                    'swap': pos.swap,
                    'entry_time': entry_time,
                    'is_open': True,
                    'position_type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL'
                }

            # Position not open, search in history
            # Get account info to use broker time
            account_info = mt5.account_info()
            if not account_info:
                self.logger.warning("Unable to get MT5 account info")
                return None

            # Search history (last 90 days or custom range)
            if end_date:
                to_date = end_date
            else:
                to_date = datetime.now()

            if start_date:
                from_date = start_date
            else:
                from_date = to_date - timedelta(days=90)

            # Get all deals for this position
            all_deals = mt5.history_deals_get(from_date, to_date)

            self.logger.info(f"[MT5] Searching history for position_id={position_id}")
            self.logger.info(f"[MT5] Date range: {from_date} to {to_date}")
            self.logger.info(f"[MT5] Total deals in range: {len(all_deals) if all_deals else 0}")

            if not all_deals or len(all_deals) == 0:
                self.logger.warning(f"[MT5] No deals found in date range")
                return None

            # CRITICAL FIX: Filter deals to only include this specific position_id
            # MT5 API bug: position parameter doesn't work, must filter manually
            deals = [deal for deal in all_deals if deal.position_id == position_id]

            self.logger.info(f"[MT5] Deals for position {position_id}: {len(deals)}")

            if not deals or len(deals) == 0:
                self.logger.warning(f"[MT5] No deals found for position {position_id}")
                return None

            # Log deals for this position
            for idx, deal in enumerate(deals):
                self.logger.info(
                    f"[MT5] Deal {idx+1}: ticket={deal.ticket}, position_id={deal.position_id}, "
                    f"entry={deal.entry}, profit={deal.profit:.2f}, commission={deal.commission:.2f}"
                )

            # Find entry and exit deals
            entry_deal = None
            exit_deal = None
            total_commission = 0.0
            total_swap = 0.0
            total_profit = 0.0

            for deal in deals:
                # Accumulate commission and swap
                total_commission += deal.commission
                total_swap += deal.swap
                total_profit += deal.profit

                # IN deal is entry
                if deal.entry == mt5.DEAL_ENTRY_IN:
                    entry_deal = deal
                # OUT deal is exit
                elif deal.entry == mt5.DEAL_ENTRY_OUT:
                    exit_deal = deal

            if not entry_deal:
                return None

            entry_time = datetime.fromtimestamp(entry_deal.time)

            # Check date filter
            if start_date and entry_time < start_date:
                return None
            if end_date and entry_time > end_date:
                return None

            return {
                'position_id': position_id,
                'symbol': entry_deal.symbol,
                'volume': entry_deal.volume,
                'entry_price': entry_deal.price,
                'exit_price': exit_deal.price if exit_deal else None,
                'profit': total_profit,
                'commission': total_commission,
                'swap': total_swap,
                'entry_time': entry_time,
                'exit_time': datetime.fromtimestamp(exit_deal.time) if exit_deal else None,
                'is_open': False,
                'position_type': 'BUY' if entry_deal.type == mt5.DEAL_TYPE_BUY else 'SELL'
            }

        except Exception as e:
            self.logger.error(f"Error fetching position {position_id} from MT5: {e}", exc_info=True)
            return None

    def get_all_channels_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_positions: int = 1
    ) -> List[ChannelStats]:
        """
        Get summary statistics for all channels

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            min_positions: Minimum number of positions to include channel

        Returns:
            List of ChannelStats sorted by net profit (descending)
        """
        channels = self.get_all_channels()
        results = []

        for channel_info in channels:
            channel_name = channel_info.get('channel_name')
            if not channel_name:
                continue

            stats = self.analyze_channel(channel_name, start_date, end_date)

            # Filter by minimum positions
            if stats.total_positions >= min_positions:
                results.append(stats)

        # Sort by net profit (descending)
        results.sort(key=lambda x: x.net_profit, reverse=True)

        return results

    def _calculate_max_drawdown(self, pnl_series: List[float]) -> float:
        """
        Calculate maximum drawdown from a series of P&L values

        Args:
            pnl_series: List of profit/loss values in chronological order

        Returns:
            Maximum drawdown as a positive number
        """
        if not pnl_series:
            return 0.0

        cumulative = 0
        peak = 0
        max_dd = 0

        for pnl in pnl_series:
            cumulative += pnl
            if cumulative > peak:
                peak = cumulative

            drawdown = peak - cumulative
            if drawdown > max_dd:
                max_dd = drawdown

        return max_dd

    def _calculate_current_drawdown(self, pnl_series: List[float]) -> float:
        """
        Calculate current drawdown from peak

        Args:
            pnl_series: List of profit/loss values in chronological order

        Returns:
            Current drawdown as a positive number
        """
        if not pnl_series:
            return 0.0

        cumulative = 0
        peak = 0

        for pnl in pnl_series:
            cumulative += pnl
            if cumulative > peak:
                peak = cumulative

        return max(0, peak - cumulative)

    def compare_channels(self, channel_names: List[str]) -> Dict[str, ChannelStats]:
        """
        Compare multiple channels side by side

        Args:
            channel_names: List of channel names to compare

        Returns:
            Dictionary mapping channel name to ChannelStats
        """
        results = {}

        for channel_name in channel_names:
            stats = self.analyze_channel(channel_name)
            results[channel_name] = stats

        return results
