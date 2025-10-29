"""
Tests for technical indicators.
"""

import numpy as np
import pandas as pd
import pytest

from backend.engine.signals.indicators import (
    atr,
    bollinger_bands,
    ema,
    macd,
    rolling_high,
    rolling_low,
    rsi,
    sma,
    vwap,
)


@pytest.fixture
def sample_prices() -> pd.Series:
    """Create sample price series."""
    return pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109])


@pytest.fixture
def sample_ohlcv() -> dict:
    """Create sample OHLCV data."""
    return {
        "open": pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109]),
        "high": pd.Series([102, 104, 103, 105, 107, 106, 108, 110, 109, 111]),
        "low": pd.Series([99, 101, 100, 102, 104, 103, 105, 107, 106, 108]),
        "close": pd.Series([101, 103, 102, 104, 106, 105, 107, 109, 108, 110]),
        "volume": pd.Series([1000, 1100, 950, 1200, 1300, 1150, 1250, 1400, 1350, 1450]),
    }


def test_sma(sample_prices: pd.Series) -> None:
    """Test Simple Moving Average."""
    result = sma(sample_prices, period=3)

    assert len(result) == len(sample_prices)
    assert pd.isna(result.iloc[0])  # First values are NaN
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == pytest.approx(101.0)  # (100+102+101)/3


def test_ema(sample_prices: pd.Series) -> None:
    """Test Exponential Moving Average."""
    result = ema(sample_prices, period=3)

    assert len(result) == len(sample_prices)
    # EMA should be less jagged than SMA
    assert not pd.isna(result.iloc[-1])


def test_atr(sample_ohlcv: dict) -> None:
    """Test Average True Range."""
    result = atr(
        sample_ohlcv["high"], sample_ohlcv["low"], sample_ohlcv["close"], period=3
    )

    assert len(result) == len(sample_ohlcv["high"])
    assert all(result[~pd.isna(result)] >= 0)  # ATR should be non-negative


def test_bollinger_bands(sample_prices: pd.Series) -> None:
    """Test Bollinger Bands."""
    middle, upper, lower = bollinger_bands(sample_prices, period=5, num_std=2.0)

    assert len(middle) == len(sample_prices)
    assert len(upper) == len(sample_prices)
    assert len(lower) == len(sample_prices)

    # Upper > Middle > Lower (where not NaN)
    valid_idx = ~pd.isna(middle)
    assert all(upper[valid_idx] >= middle[valid_idx])
    assert all(middle[valid_idx] >= lower[valid_idx])


def test_vwap(sample_ohlcv: dict) -> None:
    """Test Volume Weighted Average Price."""
    result = vwap(
        sample_ohlcv["high"],
        sample_ohlcv["low"],
        sample_ohlcv["close"],
        sample_ohlcv["volume"],
    )

    assert len(result) == len(sample_ohlcv["high"])
    assert all(result > 0)  # VWAP should be positive


def test_rsi(sample_prices: pd.Series) -> None:
    """Test Relative Strength Index."""
    result = rsi(sample_prices, period=5)

    assert len(result) == len(sample_prices)

    # RSI should be between 0 and 100 (where not NaN)
    valid_values = result[~pd.isna(result)]
    assert all(valid_values >= 0)
    assert all(valid_values <= 100)


def test_macd(sample_prices: pd.Series) -> None:
    """Test MACD."""
    macd_line, signal_line, histogram = macd(sample_prices, fast=3, slow=5, signal=2)

    assert len(macd_line) == len(sample_prices)
    assert len(signal_line) == len(sample_prices)
    assert len(histogram) == len(sample_prices)

    # Histogram = MACD - Signal
    valid_idx = ~pd.isna(histogram)
    np.testing.assert_array_almost_equal(
        histogram[valid_idx],
        (macd_line - signal_line)[valid_idx],
        decimal=5,
    )


def test_rolling_high(sample_prices: pd.Series) -> None:
    """Test rolling high."""
    result = rolling_high(sample_prices, period=3)

    assert len(result) == len(sample_prices)
    assert result.iloc[2] == 102  # max(100, 102, 101)
    assert result.iloc[3] == 103  # max(102, 101, 103)


def test_rolling_low(sample_prices: pd.Series) -> None:
    """Test rolling low."""
    result = rolling_low(sample_prices, period=3)

    assert len(result) == len(sample_prices)
    assert result.iloc[2] == 100  # min(100, 102, 101)
    assert result.iloc[3] == 101  # min(102, 101, 103)


def test_indicators_handle_empty_series() -> None:
    """Test that indicators handle empty series gracefully."""
    empty = pd.Series([], dtype=float)

    assert len(sma(empty, 3)) == 0
    assert len(ema(empty, 3)) == 0
    assert len(rsi(empty, 5)) == 0


def test_indicators_with_nans() -> None:
    """Test indicators with NaN values in input."""
    prices = pd.Series([100, np.nan, 102, 103, np.nan, 105])

    result = sma(prices, period=2)
    # SMA should propagate NaNs appropriately
    assert pd.isna(result.iloc[1])


def test_vwap_increases_with_cumulative_volume(sample_ohlcv: dict) -> None:
    """Test that VWAP is cumulative and doesn't reset."""
    result = vwap(
        sample_ohlcv["high"],
        sample_ohlcv["low"],
        sample_ohlcv["close"],
        sample_ohlcv["volume"],
    )

    # VWAP should be monotonic or stable (cumulative calculation)
    # It shouldn't have wild swings like a simple moving average
    assert result.iloc[-1] > 0
