"""
Tests for Coinbase data feed adapter.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from backend.engine.data_feed.coinbase import CoinbaseDataFeed
from backend.engine.utils.config import Settings
from backend.engine.utils.types import TimeFrame


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        coinbase_sandbox=True,
        coinbase_api_key="test_key",
        coinbase_api_secret="test_secret",
        coinbase_passphrase="test_passphrase",
    )


@pytest.fixture
def data_feed(settings: Settings) -> CoinbaseDataFeed:
    """Create CoinbaseDataFeed instance."""
    return CoinbaseDataFeed(settings)


def test_initialization(data_feed: CoinbaseDataFeed) -> None:
    """Test data feed initialization."""
    assert data_feed.sandbox is True
    assert data_feed.base_url == CoinbaseDataFeed.SANDBOX_API_URL


def test_granularity_mapping(data_feed: CoinbaseDataFeed) -> None:
    """Test timeframe to granularity conversion."""
    assert CoinbaseDataFeed.GRANULARITY_MAP[TimeFrame.ONE_MINUTE] == 60
    assert CoinbaseDataFeed.GRANULARITY_MAP[TimeFrame.FIVE_MINUTES] == 300
    assert CoinbaseDataFeed.GRANULARITY_MAP[TimeFrame.ONE_HOUR] == 3600
    assert CoinbaseDataFeed.GRANULARITY_MAP[TimeFrame.ONE_DAY] == 86400


def test_fetch_candles_default_params(data_feed: CoinbaseDataFeed) -> None:
    """Test fetching candles with default parameters."""
    # Will use synthetic data since we don't have real API credentials
    candles = data_feed.fetch_candles("BTC-USD", TimeFrame.FIVE_MINUTES, limit=10)

    assert len(candles) <= 10
    assert all(c.symbol == "BTC-USD" for c in candles)
    assert all(isinstance(c.open, Decimal) for c in candles)
    assert all(isinstance(c.high, Decimal) for c in candles)
    assert all(isinstance(c.low, Decimal) for c in candles)
    assert all(isinstance(c.close, Decimal) for c in candles)
    assert all(isinstance(c.volume, Decimal) for c in candles)

    # Candles should be sorted by timestamp
    timestamps = [c.timestamp for c in candles]
    assert timestamps == sorted(timestamps)


def test_fetch_candles_with_date_range(data_feed: CoinbaseDataFeed) -> None:
    """Test fetching candles with specific date range."""
    end = datetime.utcnow()
    start = end - timedelta(hours=1)

    candles = data_feed.fetch_candles(
        "ETH-USD",
        TimeFrame.FIVE_MINUTES,
        start=start,
        end=end,
        limit=12,
    )

    assert len(candles) <= 12
    assert all(c.symbol == "ETH-USD" for c in candles)
    assert all(start <= c.timestamp <= end for c in candles)


def test_synthetic_candles_btc(data_feed: CoinbaseDataFeed) -> None:
    """Test synthetic candle generation for BTC."""
    end = datetime.utcnow()
    start = end - timedelta(hours=1)

    candles = data_feed._generate_synthetic_candles(
        "BTC-USD",
        TimeFrame.FIVE_MINUTES,
        start,
        end,
        12,
    )

    assert len(candles) == 12

    # Check BTC price range
    for candle in candles:
        assert Decimal("30000") < candle.close < Decimal("60000")
        assert candle.high >= candle.close
        assert candle.low <= candle.close
        assert candle.high >= candle.low
        assert candle.volume > 0


def test_synthetic_candles_eth(data_feed: CoinbaseDataFeed) -> None:
    """Test synthetic candle generation for ETH."""
    end = datetime.utcnow()
    start = end - timedelta(minutes=30)

    candles = data_feed._generate_synthetic_candles(
        "ETH-USD",
        TimeFrame.FIVE_MINUTES,
        start,
        end,
        6,
    )

    assert len(candles) == 6

    # Check ETH price range
    for candle in candles:
        assert Decimal("1000") < candle.close < Decimal("4000")


def test_get_current_price(data_feed: CoinbaseDataFeed) -> None:
    """Test getting current price."""
    price_btc = data_feed.get_current_price("BTC-USD")
    assert isinstance(price_btc, Decimal)
    assert price_btc > 0

    price_eth = data_feed.get_current_price("ETH-USD")
    assert isinstance(price_eth, Decimal)
    assert price_eth > 0


def test_candle_ohlc_relationships(data_feed: CoinbaseDataFeed) -> None:
    """Test that OHLC relationships are valid."""
    candles = data_feed.fetch_candles("BTC-USD", TimeFrame.FIVE_MINUTES, limit=20)

    for candle in candles:
        # High should be highest price
        assert candle.high >= candle.open
        assert candle.high >= candle.close
        assert candle.high >= candle.low

        # Low should be lowest price
        assert candle.low <= candle.open
        assert candle.low <= candle.close
        assert candle.low <= candle.high

        # Volume should be non-negative
        assert candle.volume >= 0


@pytest.mark.asyncio
async def test_stream_candles_basic(data_feed: CoinbaseDataFeed) -> None:
    """Test basic candle streaming (with timeout)."""
    import asyncio

    count = 0
    async for candle in data_feed.stream_candles("BTC-USD", TimeFrame.ONE_MINUTE):
        assert candle.symbol == "BTC-USD"
        count += 1
        if count >= 2:  # Just test a couple iterations
            break

    assert count == 2
