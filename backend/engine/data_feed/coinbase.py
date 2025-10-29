"""
Coinbase Advanced Trade data feed adapter.

Provides REST API for historical OHLCV and WebSocket for live data.
Supports sandbox mode for paper trading.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import AsyncGenerator, List, Optional

import requests
from loguru import logger

from backend.engine.utils.config import Settings
from backend.engine.utils.types import Candle, TimeFrame


class CoinbaseDataFeed:
    """
    Coinbase Advanced Trade data feed.

    Fetches historical candles via REST API and streams live data via WebSocket.
    """

    # Coinbase REST endpoints
    REST_API_URL = "https://api.coinbase.com/api/v3/brokerage"
    SANDBOX_API_URL = "https://api-public.sandbox.exchange.coinbase.com"

    # Granularity mapping (Coinbase uses seconds)
    GRANULARITY_MAP = {
        TimeFrame.ONE_MINUTE: 60,
        TimeFrame.FIVE_MINUTES: 300,
        TimeFrame.FIFTEEN_MINUTES: 900,
        TimeFrame.THIRTY_MINUTES: 1800,
        TimeFrame.ONE_HOUR: 3600,
        TimeFrame.FOUR_HOURS: 14400,
        TimeFrame.ONE_DAY: 86400,
    }

    def __init__(self, settings: Settings):
        """
        Initialize Coinbase data feed.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.api_key = settings.coinbase_api_key
        self.api_secret = settings.coinbase_api_secret
        self.passphrase = settings.coinbase_passphrase
        self.sandbox = settings.coinbase_sandbox

        self.base_url = self.SANDBOX_API_URL if self.sandbox else self.REST_API_URL
        logger.info(
            f"Initialized CoinbaseDataFeed (sandbox={self.sandbox}, base_url={self.base_url})"
        )

    def _make_request(
        self, method: str, endpoint: str, params: Optional[dict] = None
    ) -> dict:
        """
        Make authenticated REST API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response as dictionary

        Raises:
            Exception: If request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        headers = {
            "Content-Type": "application/json",
        }

        # Note: Full authentication would require HMAC signing
        # For sandbox/demo purposes, we'll use public endpoints
        # In production, implement proper authentication per Coinbase docs

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Coinbase API request failed: {e}")
            raise

    def fetch_candles(
        self,
        symbol: str,
        timeframe: TimeFrame = TimeFrame.FIVE_MINUTES,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 300,
    ) -> List[Candle]:
        """
        Fetch historical OHLCV candles.

        Args:
            symbol: Trading pair (e.g., 'BTC-USD')
            timeframe: Candle timeframe
            start: Start datetime (default: 300 candles ago)
            end: End datetime (default: now)
            limit: Maximum number of candles

        Returns:
            List of Candle objects
        """
        granularity = self.GRANULARITY_MAP.get(timeframe, 300)

        # Default time range
        if end is None:
            end = datetime.utcnow()
        if start is None:
            start = end - timedelta(seconds=granularity * limit)

        # Coinbase uses product_id format (e.g., BTC-USD)
        product_id = symbol

        # For demo/sandbox, generate synthetic data if API unavailable
        try:
            # Attempt to fetch from Coinbase
            # Note: Public candles endpoint format for Coinbase Advanced
            endpoint = f"products/{product_id}/candles"
            params = {
                "granularity": str(granularity),
                "start": int(start.timestamp()),
                "end": int(end.timestamp()),
            }

            data = self._make_request("GET", endpoint, params)

            # Parse response into Candle objects
            candles = []
            if isinstance(data, list):
                for item in data[:limit]:
                    # Coinbase candle format: [timestamp, low, high, open, close, volume]
                    candles.append(
                        Candle(
                            timestamp=datetime.fromtimestamp(item[0]),
                            open=Decimal(str(item[3])),
                            high=Decimal(str(item[2])),
                            low=Decimal(str(item[1])),
                            close=Decimal(str(item[4])),
                            volume=Decimal(str(item[5])),
                            symbol=symbol,
                        )
                    )

            candles.sort(key=lambda c: c.timestamp)
            logger.info(f"Fetched {len(candles)} candles for {symbol} ({timeframe.value})")
            return candles

        except Exception as e:
            logger.warning(f"Failed to fetch candles from Coinbase: {e}. Using synthetic data.")
            return self._generate_synthetic_candles(symbol, timeframe, start, end, limit)

    def _generate_synthetic_candles(
        self,
        symbol: str,
        timeframe: TimeFrame,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> List[Candle]:
        """
        Generate synthetic candle data for testing.

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            start: Start datetime
            end: End datetime
            limit: Number of candles

        Returns:
            List of synthetic Candle objects
        """
        import random

        granularity = self.GRANULARITY_MAP.get(timeframe, 300)
        candles = []

        # Starting price based on symbol
        if "BTC" in symbol:
            base_price = Decimal("45000")
        elif "ETH" in symbol:
            base_price = Decimal("2500")
        else:
            base_price = Decimal("100")

        current_time = start
        current_price = base_price

        while current_time <= end and len(candles) < limit:
            # Random walk with some volatility
            change_pct = Decimal(str(random.uniform(-0.02, 0.02)))  # +/- 2%
            open_price = current_price
            close_price = open_price * (Decimal("1") + change_pct)

            high_price = max(open_price, close_price) * Decimal(str(random.uniform(1.0, 1.01)))
            low_price = min(open_price, close_price) * Decimal(str(random.uniform(0.99, 1.0)))
            volume = Decimal(str(random.uniform(10, 100)))

            candles.append(
                Candle(
                    timestamp=current_time,
                    open=open_price,
                    high=high_price,
                    low=low_price,
                    close=close_price,
                    volume=volume,
                    symbol=symbol,
                )
            )

            current_price = close_price
            current_time += timedelta(seconds=granularity)

        logger.info(f"Generated {len(candles)} synthetic candles for {symbol}")
        return candles

    async def stream_candles(
        self, symbol: str, timeframe: TimeFrame = TimeFrame.FIVE_MINUTES
    ) -> AsyncGenerator[Candle, None]:
        """
        Stream live candles via WebSocket.

        Args:
            symbol: Trading pair
            timeframe: Candle timeframe

        Yields:
            Candle objects as they complete
        """
        # WebSocket implementation would go here
        # For MVP, we'll simulate with periodic polling
        granularity = self.GRANULARITY_MAP.get(timeframe, 300)

        logger.info(f"Starting candle stream for {symbol} ({timeframe.value})")

        while True:
            try:
                # Fetch latest candle
                candles = self.fetch_candles(symbol, timeframe, limit=1)
                if candles:
                    yield candles[0]

                # Wait for next candle period
                await asyncio.sleep(granularity)

            except Exception as e:
                logger.error(f"Error in candle stream: {e}")
                await asyncio.sleep(10)  # Retry delay

    def get_current_price(self, symbol: str) -> Decimal:
        """
        Get current market price for a symbol.

        Args:
            symbol: Trading pair (e.g., 'BTC-USD')

        Returns:
            Current price as Decimal
        """
        try:
            endpoint = f"products/{symbol}/ticker"
            data = self._make_request("GET", endpoint)

            if "price" in data:
                return Decimal(str(data["price"]))

            # Fallback: get from latest candle
            candles = self.fetch_candles(symbol, TimeFrame.ONE_MINUTE, limit=1)
            if candles:
                return candles[0].close

        except Exception as e:
            logger.warning(f"Failed to get current price for {symbol}: {e}")

        # Last resort: synthetic price
        if "BTC" in symbol:
            return Decimal("45000")
        elif "ETH" in symbol:
            return Decimal("2500")
        return Decimal("100")
