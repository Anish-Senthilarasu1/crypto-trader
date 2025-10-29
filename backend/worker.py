"""
Live paper trading worker.

Orchestrates data feed, strategies, risk management, and order execution.
"""

import sys
import time
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Dict, Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger

from backend.engine.broker.coinbase_paper import CoinbasePaperBroker
from backend.engine.data_feed.coinbase import CoinbaseDataFeed
from backend.engine.risk.limits import RiskLimits, RiskLimitsConfig
from backend.engine.risk.position import PositionSizer, PositionSizeConfig
from backend.engine.signals.momentum import MomentumConfig, MomentumStrategy
from backend.engine.store.sqlite import SQLiteStore
from backend.engine.utils.config import get_settings
from backend.engine.utils.types import OrderSide, OrderType, TimeFrame, Trade


class TradingWorker:
    """
    Live paper trading worker.

    Runs strategy analysis on schedule and executes trades.
    """

    def __init__(self) -> None:
        """Initialize trading worker."""
        self.settings = get_settings()

        # Initialize components
        logger.info("Initializing trading worker...")

        self.data_feed = CoinbaseDataFeed(self.settings)
        self.broker = CoinbasePaperBroker(self.settings)
        self.store = SQLiteStore(self.settings.database_url.replace("sqlite:///", ""))

        # Strategy (use momentum by default)
        self.strategy = MomentumStrategy(
            MomentumConfig(
                lookback_period=20,
                atr_period=14,
                atr_multiplier=2.0,
                trail_atr_multiplier=1.5,
            )
        )

        # Risk management
        self.position_sizer = PositionSizer(
            PositionSizeConfig(risk_per_trade=self.settings.risk_per_trade)
        )

        self.risk_limits = RiskLimits(
            RiskLimitsConfig(
                max_daily_loss=self.settings.max_daily_loss,
                max_portfolio_exposure=self.settings.max_portfolio_exposure,
                symbol_whitelist=self.settings.symbols,
            )
        )

        # State tracking
        self.active_positions: Dict[str, dict] = {}  # symbol -> position info
        self.last_signals: Dict[str, datetime] = {}  # Debounce duplicate signals

        # Initialize daily equity
        account = self.broker.get_account()
        self.risk_limits.update_daily_equity(account.equity)

        logger.info(
            f"✅ Trading worker initialized (equity: ${account.equity}, "
            f"symbols: {self.settings.symbols})"
        )

    def run_trading_loop(self) -> None:
        """Main trading loop - called on schedule."""
        try:
            logger.info("🔄 Running trading loop...")

            # Check if trading is enabled
            if self.risk_limits.kill_switch_active:
                logger.warning("⚠️  Kill switch active - skipping trading loop")
                return

            # Get account state
            account = self.broker.get_account()
            logger.info(f"Account: equity=${account.equity}, cash=${account.cash}")

            # Update position prices
            current_prices = {}
            for symbol in self.settings.symbols:
                try:
                    price = self.data_feed.get_current_price(symbol)
                    current_prices[symbol] = price
                except Exception as e:
                    logger.error(f"Failed to get price for {symbol}: {e}")

            self.broker.update_position_prices(current_prices)

            # Check exits for active positions
            self._check_exits()

            # Look for new entries
            self._check_entries(account)

            # Save account snapshot
            account = self.broker.get_account()
            self.store.save_account_snapshot(
                account.equity,
                account.cash,
                account.positions_value,
                account.unrealized_pnl,
                account.realized_pnl,
            )

            logger.info("✅ Trading loop complete")

        except Exception as e:
            logger.exception(f"Error in trading loop: {e}")

    def _check_entries(self, account) -> None:
        """Check for new entry signals."""
        for symbol in self.settings.symbols:
            # Skip if already have position
            if symbol in self.active_positions:
                logger.debug(f"Skipping {symbol} - already have position")
                continue

            # Skip if recently signaled (debounce)
            if symbol in self.last_signals:
                elapsed = (datetime.utcnow() - self.last_signals[symbol]).total_seconds()
                if elapsed < 300:  # 5 min debounce
                    continue

            try:
                # Fetch candles
                candles = self.data_feed.fetch_candles(
                    symbol,
                    TimeFrame.FIVE_MINUTES,
                    limit=100,
                )

                if not candles:
                    logger.warning(f"No candles for {symbol}")
                    continue

                # Run strategy
                signal = self.strategy.analyze(candles)

                if signal:
                    logger.info(f"📊 Signal: {symbol} @ ${signal.entry_price}")
                    self._execute_entry(signal, account)
                    self.last_signals[symbol] = datetime.utcnow()

            except Exception as e:
                logger.error(f"Error checking entry for {symbol}: {e}")

    def _execute_entry(self, signal, account) -> None:
        """Execute entry order based on signal."""
        try:
            # Calculate position size
            size = self.position_sizer.calculate_size(
                account.equity,
                signal.entry_price,
                signal.stop_loss,
                signal.atr_value,
            )

            if size <= 0:
                logger.warning(f"Invalid position size: {size}")
                return

            order_value = size * signal.entry_price

            # Check risk limits
            allowed, reason = self.risk_limits.check_order(
                signal.symbol,
                order_value,
                account.positions_value,
                account.equity,
                len(self.active_positions),
            )

            if not allowed:
                logger.warning(f"Order rejected: {reason}")
                return

            # Place order
            order = self.broker.place_order(
                symbol=signal.symbol,
                side=signal.side,
                quantity=size,
                order_type=OrderType.MARKET,
            )

            self.store.save_order(order)

            # Simulate immediate fill (for paper trading)
            fill = self.broker.fill_order(order.order_id, signal.entry_price)

            if fill:
                self.store.save_fill(fill)
                self.store.save_order(order)  # Update order status

                # Track position
                self.active_positions[signal.symbol] = {
                    "order_id": order.order_id,
                    "entry_price": signal.entry_price,
                    "stop_loss": signal.stop_loss,
                    "trailing_stop": signal.trailing_stop,
                    "quantity": size,
                    "entry_time": datetime.utcnow(),
                    "atr": signal.atr_value,
                    "strategy": "momentum",
                }

                logger.info(
                    f"✅ Entered {signal.symbol}: {size} @ ${signal.entry_price} "
                    f"(stop: ${signal.stop_loss})"
                )

        except Exception as e:
            logger.exception(f"Error executing entry: {e}")

    def _check_exits(self) -> None:
        """Check if any positions should be exited."""
        symbols_to_remove = []

        for symbol, pos_info in self.active_positions.items():
            try:
                # Get current price
                current_price = self.data_feed.get_current_price(symbol)

                # Update trailing stop
                new_stop = self.strategy.update_trailing_stop(
                    pos_info["entry_price"],
                    current_price,
                    pos_info["stop_loss"],
                    pos_info["atr"],
                )

                if new_stop != pos_info["stop_loss"]:
                    logger.info(
                        f"Updated trailing stop for {symbol}: "
                        f"${pos_info['stop_loss']} -> ${new_stop}"
                    )
                    pos_info["stop_loss"] = new_stop

                # Check if should exit
                should_exit = self.strategy.should_exit(
                    pos_info["entry_price"],
                    current_price,
                    pos_info["stop_loss"],
                )

                if should_exit:
                    logger.info(f"🚪 Exiting {symbol} at ${current_price}")
                    self._execute_exit(symbol, current_price, pos_info)
                    symbols_to_remove.append(symbol)

            except Exception as e:
                logger.error(f"Error checking exit for {symbol}: {e}")

        # Remove closed positions
        for symbol in symbols_to_remove:
            del self.active_positions[symbol]

    def _execute_exit(self, symbol: str, exit_price: Decimal, pos_info: dict) -> None:
        """Execute exit order."""
        try:
            # Place sell order
            order = self.broker.place_order(
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=pos_info["quantity"],
                order_type=OrderType.MARKET,
            )

            self.store.save_order(order)

            # Simulate fill
            fill = self.broker.fill_order(order.order_id, exit_price)

            if fill:
                self.store.save_fill(fill)
                self.store.save_order(order)

                # Calculate P&L
                entry = pos_info["entry_price"]
                quantity = pos_info["quantity"]
                pnl = (exit_price - entry) * quantity
                pnl_pct = (exit_price - entry) / entry * Decimal("100")

                # Record trade
                trade = Trade(
                    trade_id=f"trade_{uuid.uuid4().hex[:16]}",
                    symbol=symbol,
                    side=OrderSide.BUY,
                    entry_price=entry,
                    exit_price=exit_price,
                    quantity=quantity,
                    entry_time=pos_info["entry_time"],
                    exit_time=datetime.utcnow(),
                    pnl=pnl,
                    pnl_percent=pnl_pct,
                    fees=order.fees,
                    strategy=pos_info.get("strategy", "unknown"),
                )

                self.store.save_trade(trade)
                self.risk_limits.record_trade_pnl(pnl)

                logger.info(
                    f"✅ Exited {symbol}: {quantity} @ ${exit_price} "
                    f"(P&L: ${pnl:.2f}, {pnl_pct:.2f}%)"
                )

        except Exception as e:
            logger.exception(f"Error executing exit: {e}")

    def start(self) -> None:
        """Start the worker with scheduler."""
        # Configure logger
        logger.remove()
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            level=self.settings.log_level,
        )
        logger.add(
            "logs/worker.log",
            rotation="1 day",
            retention="30 days",
            level="DEBUG",
        )

        # Run once immediately
        logger.info("🚀 Starting trading worker...")
        self.run_trading_loop()

        if not self.settings.worker_enabled:
            logger.info("Worker disabled in config - exiting after single run")
            return

        # Setup scheduler
        scheduler = BlockingScheduler()

        scheduler.add_job(
            self.run_trading_loop,
            "interval",
            seconds=self.settings.worker_check_interval_seconds,
            id="trading_loop",
        )

        logger.info(
            f"⏰ Scheduled trading loop every {self.settings.worker_check_interval_seconds}s"
        )

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("🛑 Shutting down trading worker...")
            self.store.close()


def main() -> None:
    """Main entry point."""
    worker = TradingWorker()
    worker.start()


if __name__ == "__main__":
    main()
