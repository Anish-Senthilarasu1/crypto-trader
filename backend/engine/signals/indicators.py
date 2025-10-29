"""
Technical indicators for trading strategies.

All functions accept pandas Series/DataFrame and return numpy arrays or Series.
"""

from decimal import Decimal
from typing import Tuple

import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    """
    Simple Moving Average.

    Args:
        series: Price series
        period: Moving average period

    Returns:
        SMA series
    """
    return series.rolling(window=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """
    Exponential Moving Average.

    Args:
        series: Price series
        period: EMA period

    Returns:
        EMA series
    """
    return series.ewm(span=period, adjust=False).mean()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Average True Range (volatility indicator).

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ATR period (default: 14)

    Returns:
        ATR series
    """
    # True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
    prev_close = close.shift(1)

    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # ATR is EMA of true range
    return true_range.ewm(span=period, adjust=False).mean()


def bollinger_bands(
    series: pd.Series, period: int = 20, num_std: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands.

    Args:
        series: Price series
        period: Moving average period (default: 20)
        num_std: Number of standard deviations (default: 2.0)

    Returns:
        Tuple of (middle_band, upper_band, lower_band)
    """
    middle = sma(series, period)
    std = series.rolling(window=period).std()

    upper = middle + (std * num_std)
    lower = middle - (std * num_std)

    return middle, upper, lower


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Volume Weighted Average Price.

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        volume: Volume

    Returns:
        VWAP series
    """
    typical_price = (high + low + close) / 3
    cumulative_tpv = (typical_price * volume).cumsum()
    cumulative_volume = volume.cumsum()

    return cumulative_tpv / cumulative_volume


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index.

    Args:
        series: Price series
        period: RSI period (default: 14)

    Returns:
        RSI series (0-100)
    """
    delta = series.diff()

    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)

    avg_gains = gains.ewm(span=period, adjust=False).mean()
    avg_losses = losses.ewm(span=period, adjust=False).mean()

    rs = avg_gains / avg_losses
    rsi_values = 100 - (100 / (1 + rs))

    return rsi_values


def macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Moving Average Convergence Divergence.

    Args:
        series: Price series
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
        signal: Signal line period (default: 9)

    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)

    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def rolling_high(series: pd.Series, period: int) -> pd.Series:
    """
    Rolling maximum (highest high over period).

    Args:
        series: Price series
        period: Lookback period

    Returns:
        Rolling high series
    """
    return series.rolling(window=period).max()


def rolling_low(series: pd.Series, period: int) -> pd.Series:
    """
    Rolling minimum (lowest low over period).

    Args:
        series: Price series
        period: Lookback period

    Returns:
        Rolling low series
    """
    return series.rolling(window=period).min()


def stochastic(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14, smooth_k: int = 3
) -> Tuple[pd.Series, pd.Series]:
    """
    Stochastic Oscillator.

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: Lookback period (default: 14)
        smooth_k: K smoothing period (default: 3)

    Returns:
        Tuple of (%K, %D)
    """
    lowest_low = rolling_low(low, period)
    highest_high = rolling_high(high, period)

    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    k_smooth = sma(k, smooth_k)
    d = sma(k_smooth, 3)

    return k_smooth, d


def donchian_channels(
    high: pd.Series, low: pd.Series, period: int = 20
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Donchian Channels.

    Args:
        high: High prices
        low: Low prices
        period: Lookback period (default: 20)

    Returns:
        Tuple of (upper_channel, middle_channel, lower_channel)
    """
    upper = rolling_high(high, period)
    lower = rolling_low(low, period)
    middle = (upper + lower) / 2

    return upper, middle, lower
