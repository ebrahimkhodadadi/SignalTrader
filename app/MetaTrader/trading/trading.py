from datetime import datetime
from loguru import logger
import Database
from Database import Migrations
from ..connection import AccountConfig


class TradingOperations:
    """High-level trading operations and signal processing"""

    @staticmethod
    def _get_mt_account_config():
        """Get MetaTrader account configuration from settings"""
        from Configure.settings.Settings import Settings
        return AccountConfig({
            'server': Settings.mt_server(),
            'username': Settings.mt_username(),
            'password': Settings.mt_password(),
            'path': Settings.mt_path(),
            'lot': Settings.mt_lot(),
            'HighRisk': Settings.mt_high_risk(),
            'SaveProfits': Settings.mt_save_profits(),
            'AccountSize': Settings.mt_account_size(),
            'CloserPrice': Settings.mt_closer_price(),
            'expirePendinOrderInMinutes': Settings.mt_expire_pending_orders_minutes(),
            'ClosePositionsOnTrail': Settings.mt_close_positions_on_trail(),
            'disableCache': Settings.disable_cache(),
            'SymbolMappings': Settings.mt_symbol_mappings()
        })

    @staticmethod
    def _create_metatrader_instance(account_config, save_profits=None):
        """Create MetaTrader instance with given account config"""
        from ..MetaTrader import MetaTrader
        mt_kwargs = {
            'path': account_config.path,
            'server': account_config.server,
            'user': account_config.username,
            'password': account_config.password
        }
        if save_profits is not None:
            mt_kwargs['saveProfits'] = save_profits
        return MetaTrader(**mt_kwargs)

    @staticmethod
    def trade(message_username, message_id, message_chatid, actionType, symbol, openPrice, secondPrice, tp_list, sl, comment, provider="telegram"):
        """Execute a complete trading operation"""
        # logger.debug(f"Processing trade signal: {actionType.name} {symbol}")

        mtAccount = TradingOperations._get_mt_account_config()

        # Convert action type
        if actionType.value == 1:  # buy
            actionType = 0  # mt5.ORDER_TYPE_BUY
        elif actionType.value == 2:  # sell
            actionType = 1  # mt5.ORDER_TYPE_SELL

        mt = TradingOperations._create_metatrader_instance(mtAccount)
        if not mt.Login():
            logger.error("Failed to login to MetaTrader")
            return
        if not mt.CheckSymbol(symbol):
            logger.error(f"Symbol {symbol} not available")
            return

        # Validate prices
        openPrice = mt.validate(actionType, openPrice, symbol)
        sl = mt.validate(actionType, sl, symbol, openPrice, isSl=True)
        if secondPrice is not None and secondPrice != 0:
            secondPrice = mt.validate(
                actionType, secondPrice, symbol, isSecondPrice=True)
            if (actionType == 0 and openPrice > secondPrice) or (actionType == 1 and openPrice < secondPrice):
                openPrice, secondPrice = secondPrice, openPrice

        if tp_list is None:
            logger.warning("No take profit levels specified")
            return

        validated_tp_levels = mt.validate_tp_list(
            actionType, tp_list, symbol, openPrice, secondPrice, mtAccount.CloserPrice)

        # Validate that we have take profit levels
        if not validated_tp_levels:
            logger.warning("No valid take profit levels found")
            return

        # Prepare position opening parameters first
        tp_levels = sorted(validated_tp_levels)
        if actionType == 0:  # BUY
            tp = max(tp_levels)
        else:  # SELL
            tp = min(tp_levels)

        # First position parameters
        first_lot = mt.calculate_lot_size_with_prices(
            symbol, mtAccount.lot, openPrice, sl, mtAccount.account_size)

        position_params = []

        # Add first position parameters
        first_params = {
            'actionType': actionType,
            'lot': first_lot,
            'symbol': symbol,
            'sl': sl,
            'tp': tp,
            'price': openPrice,
            'expirePendinOrderInMinutes': mtAccount.expirePendinOrderInMinutes,
            'comment': comment,
            'signal_id': None,  # Will be set after signal creation
            'closerPrice': mtAccount.CloserPrice,
            'isFirst': True,
            'isSecond': False,
            'position_name': 'first'
        }
        position_params.append(first_params)

        # Add second position parameters if high risk mode enabled
        if secondPrice is not None and secondPrice != 0 and mtAccount.HighRisk == True:
            second_lot = mt.calculate_lot_size_with_prices(
                symbol, mtAccount.lot, secondPrice, sl, mtAccount.account_size)
            secondPrice = mt.validate(actionType, secondPrice, symbol)

            second_params = {
                'actionType': actionType,
                'lot': second_lot,
                'symbol': symbol,
                'sl': sl,
                'tp': tp,
                'price': secondPrice,
                'expirePendinOrderInMinutes': mtAccount.expirePendinOrderInMinutes,
                'comment': comment,
                'signal_id': None,  # Will be set after signal creation
                'closerPrice': mtAccount.CloserPrice,
                'isFirst': False,
                'isSecond': True,
                'position_name': 'second'
            }
            position_params.append(second_params)

        # Save to database with transaction for atomicity
        import sqlite3
        signal_id = None
        try:
            # Use transaction for atomic signal + position inserts
            conn = Migrations.signal_repo._connect()
            conn.execute("BEGIN TRANSACTION")

            # Determine signal type from actionType
            import MetaTrader5 as mt5
            signal_type = "BUY" if actionType in [mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP] else "SELL"

            signal_data = {
                "provider": provider,
                "signal_type": signal_type,
                "telegram_channel_title": message_username,
                "telegram_message_id": message_id,
                "telegram_message_chatid": message_chatid,
                "open_price": openPrice,
                "second_price": secondPrice,
                "stop_loss": sl,
                "tp_list": ','.join(map(str, validated_tp_levels)) if validated_tp_levels else '',
                "symbol": symbol,
                "current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            signal_id = Migrations.signal_repo.insert(signal_data)

            # Update signal_id in position params
            for params in position_params:
                params['signal_id'] = signal_id

            conn.commit()
            logger.debug(f"Signal {signal_id} saved to database atomically")

        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise
        finally:
            if 'conn' in locals():
                conn.close()

        # Execute position openings sequentially
        if position_params:
            for params in position_params:
                mt.OpenPosition(
                    params['actionType'], params['lot'], params['symbol'], params['sl'], params['tp'], params['price'],
                    params['expirePendinOrderInMinutes'], params['comment'], params['signal_id'],
                    params['closerPrice'], params['isFirst'], params['isSecond']
                )

    @staticmethod
    def risk_free_positions(chat_id, message_id):
        """Move stop loss to entry price for risk-free positions - Optimized for performance"""
        import concurrent.futures
        import threading

        logger.info(
            f"Applying risk-free strategy for chat {chat_id}, message {message_id}")

        mtAccount = TradingOperations._get_mt_account_config()
        mt = TradingOperations._create_metatrader_instance(mtAccount)

        if not mt.Login():
            logger.error("Failed to login for risk-free operation")
            return

        # Get position tickets for this signal
        position_tickets = Migrations.get_last_signal_positions_by_chatid_and_messageid(
            chat_id, message_id)

        if not position_tickets:
            logger.warning(f"No positions found for chat {chat_id}, message {message_id}")
            return

        # Batch database queries to reduce round trips
        logger.debug(f"Processing {len(position_tickets)} positions for risk-free operation")

        # Get all open positions at once
        all_open_positions = mt.get_open_positions()
        relevant_positions = [pos for pos in all_open_positions if pos.ticket in position_tickets]

        if not relevant_positions:
            logger.warning("No open positions found for risk-free operation")
            return

        # Batch fetch signal data for all positions
        signal_data_cache = {}
        position_data_cache = {}

        for position in relevant_positions:
            ticket = position.ticket

            # Cache signal data
            if ticket not in signal_data_cache:
                signal = Database.Migrations.get_signal_by_positionId(ticket)
                if signal:
                    signal_data_cache[ticket] = signal

                    # Cache position data for this signal
                    if signal["id"] not in position_data_cache:
                        position_data = Database.Migrations.get_position_by_signal_id(
                            signal["id"], first=True)
                        position_data_cache[signal["id"]] = position_data

        # Process positions with parallel MT5 operations
        def process_single_position(position):
            """Process a single position for risk-free operation"""
            ticket = position.ticket

            # Get cached signal data
            signal = signal_data_cache.get(ticket)
            if not signal:
                logger.error(f"Signal data not found for position {ticket}")
                return False

            # Determine entry price
            entry_price = signal["open_price"]

            # Check if we have position data and get actual entry price
            signal_id = signal["id"]
            position_data = position_data_cache.get(signal_id)
            if position_data is not None:
                # Get current position data from MT5
                current_pos = mt.get_position_or_order(ticket_id=position_data["position_id"])
                if current_pos is not None:
                    entry_price = current_pos.price_open

            logger.debug(f"Moving SL to entry price {entry_price} for position {ticket}")

            # Update stop loss
            sl_result = mt.update_stop_loss(ticket, entry_price)
            if sl_result:
                # Close half position only if not in high risk mode
                if mtAccount.HighRisk:
                    logger.debug(f"Closing half position {ticket} for profit protection")
                    # Close half position
                    mt.close_half_position(ticket)
                return True
            else:
                logger.warning(f"Failed to update stop loss for position {ticket}")
                return False

        # Use ThreadPoolExecutor for parallel MT5 operations
        successful_operations = 0
        max_workers = min(len(relevant_positions), 5)  # Limit concurrent operations

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_position = {
                executor.submit(process_single_position, position): position
                for position in relevant_positions
            }

            # Collect results
            for future in concurrent.futures.as_completed(future_to_position):
                position = future_to_position[future]
                try:
                    result = future.result()
                    if result:
                        successful_operations += 1
                except Exception as e:
                    logger.error(f"Error processing position {position.ticket}: {e}")

        logger.success(f"Risk-free operation completed: {successful_operations}/{len(relevant_positions)} positions processed successfully")

    @staticmethod
    def update_last_signal(chat_id, stop_loss):
        """Update stop loss for last signal"""
        logger.info(
            f"Updating stop loss to {stop_loss} for last signal in chat {chat_id}")

        account = TradingOperations._get_mt_account_config()
        mt = TradingOperations._create_metatrader_instance(account, save_profits=account.SaveProfits)

        stop_loss = float(stop_loss)
        positions = Database.Migrations.get_last_signal_positions_by_chatid(
            chat_id)

        signal = Migrations.get_signal_by_positionId(positions[0])
        if signal is None or len(str(signal['stop_loss'])) != len(str(stop_loss)):
            logger.warning("Signal not found or stop loss format mismatch")
            return

        result = False
        for position in positions:
            result = mt.update_stop_loss(position, stop_loss)

        if result:
            Migrations.update_stoploss(signal['id'], stop_loss)
            logger.success(
                f"Stop loss updated to {stop_loss} for signal {signal['id']}")

    @staticmethod
    def update_signal(signal_id, takeProfits, stopLoss):
        """Update signal take profits and stop loss"""
        logger.info(
            f"Updating signal {signal_id} - SL: {stopLoss}, TP: {takeProfits}")

        account = TradingOperations._get_mt_account_config()
        mt = TradingOperations._create_metatrader_instance(account, save_profits=account.SaveProfits)

        stopLoss = float(stopLoss)
        positions = Migrations.get_positions_by_signalid(signal_id)

        signal = Migrations.get_signal_by_id(signal_id)
        if signal is None or len(str(signal['stop_loss'])) != len(str(stopLoss)):
            logger.warning(
                f"Signal {signal_id} not found or stop loss format mismatch")
            return

        result = False
        for position in positions:
            result = mt.update_stop_loss(position["position_id"], stopLoss)

        if result:
            Migrations.update_stoploss(signal_id, stopLoss)
            logger.success(f"Stop loss updated for signal {signal_id}")

        Migrations.update_takeProfits(signal_id, takeProfits)
        logger.success(f"Take profits updated for signal {signal_id}")

    @staticmethod
    def delete_signal(signal_id):
        """Delete signal and close all related positions"""
        logger.info(f"Deleting signal {signal_id} and closing all positions")

        account = TradingOperations._get_mt_account_config()
        mt = TradingOperations._create_metatrader_instance(account, save_profits=account.SaveProfits)

        positions = Migrations.get_positions_by_signalid(signal_id)
        if not positions:
            logger.warning(f"No positions found for signal {signal_id}")
            return

        # Process position closures sequentially
        successful_closures = 0
        for position in positions:
            if mt.close_position(position["position_id"]):
                successful_closures += 1

        logger.success(f"Signal {signal_id} deleted - {successful_closures}/{len(positions)} positions closed successfully")

    @staticmethod
    def close_half_signal(signal_id):
        """Close half of positions for a signal"""
        logger.info(f"Closing half positions for signal {signal_id}")

        account = TradingOperations._get_mt_account_config()
        mt = TradingOperations._create_metatrader_instance(account, save_profits=account.SaveProfits)

        positions = Migrations.get_positions_by_signalid(signal_id)
        if not positions:
            logger.warning(f"No positions found for signal {signal_id}")
            return

        # Process positions sequentially
        successful_operations = 0
        for position in positions:
            position_obj = mt.get_position_or_order(position["position_id"])
            if position_obj is not None:
                mt.close_half_position(position["position_id"])
                mt.update_stop_loss(position["position_id"], position_obj.price_open)
                successful_operations += 1

        logger.success(f"Half-close operation completed for {successful_operations}/{len(positions)} positions in signal {signal_id}")
