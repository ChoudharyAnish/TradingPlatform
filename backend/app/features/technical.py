"""Timestamp-aware technical feature engineering (no look-ahead)."""

from __future__ import annotations

import numpy as np
import pandas as pd


FEATURE_SET_VERSION = "v1"


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def compute_technical_features(ohlcv: pd.DataFrame, index_close: pd.Series | None = None) -> pd.DataFrame:
    """
    Compute features using only information available at each row's trade_date.
    All rolling stats are trailing (past-inclusive of current close for EOD research).
    Targets must be shifted separately when training.
    """
    df = ohlcv.sort_values("trade_date").copy()
    c = df["adjusted_close"].astype(float)
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    v = df["volume"].astype(float)

    out = pd.DataFrame({"trade_date": df["trade_date"]})

    # returns / structure
    out["ret_1"] = c.pct_change(1)
    out["ret_5"] = c.pct_change(5)
    out["ret_20"] = c.pct_change(20)
    out["gap"] = (df["open"].astype(float) - c.shift(1)) / c.shift(1)
    out["hl_range"] = (h - l) / c
    out["roll_high_20"] = c / c.rolling(20).max()
    out["roll_low_20"] = c / c.rolling(20).min()

    # trend
    out["sma_20"] = c.rolling(20).mean() / c - 1
    out["sma_50"] = c.rolling(50).mean() / c - 1
    out["ema_12"] = _ema(c, 12) / c - 1
    out["ema_26"] = _ema(c, 26) / c - 1
    macd = _ema(c, 12) - _ema(c, 26)
    signal = _ema(macd, 9)
    out["macd"] = macd / c
    out["macd_signal"] = signal / c
    out["macd_hist"] = (macd - signal) / c

    # ADX (simplified)
    up = h.diff()
    down = -l.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = pd.concat([(h - l), (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean()
    plus_di = 100 * pd.Series(plus_dm, index=df.index).rolling(14).mean() / atr14
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(14).mean() / atr14
    dx = (100 * (plus_di - minus_di).abs() / (plus_di + minus_di)).replace([np.inf, -np.inf], np.nan)
    out["adx_14"] = dx.rolling(14).mean()
    out["atr_14"] = atr14 / c

    # momentum
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    out["rsi_14"] = 100 - (100 / (1 + rs))
    low14 = l.rolling(14).min()
    high14 = h.rolling(14).max()
    out["stoch_k"] = 100 * (c - low14) / (high14 - low14).replace(0, np.nan)
    out["roc_10"] = c.pct_change(10)

    # volatility
    out["vol_20"] = c.pct_change().rolling(20).std()
    mid = c.rolling(20).mean()
    std = c.rolling(20).std()
    out["bb_upper"] = (mid + 2 * std) / c - 1
    out["bb_lower"] = (mid - 2 * std) / c - 1
    out["bb_width"] = (4 * std) / mid

    # volume
    out["vol_sma_20"] = v / v.rolling(20).mean() - 1
    out["rel_volume"] = v / v.rolling(20).mean()
    direction = np.sign(c.diff()).fillna(0)
    out["obv_slope"] = (direction * v).rolling(20).sum() / (v.rolling(20).sum() + 1e-9)

    # market context / relative strength
    if index_close is not None and len(index_close) == len(c):
        idx = index_close.astype(float).reset_index(drop=True)
        stock = c.reset_index(drop=True)
        out["nifty_ret_20"] = idx.pct_change(20)
        out["rel_strength_20"] = stock.pct_change(20) - idx.pct_change(20)
        out["market_vol_20"] = idx.pct_change().rolling(20).std()
    else:
        out["nifty_ret_20"] = np.nan
        out["rel_strength_20"] = np.nan
        out["market_vol_20"] = np.nan

    out["close"] = c.values
    return out


def make_classification_target(close: pd.Series, horizon: int, threshold: float = 0.005) -> pd.Series:
    """Future return label — must only be used as y, never as a feature."""
    fwd = close.shift(-horizon) / close - 1
    label = pd.Series(np.where(fwd > threshold, "UP", np.where(fwd < -threshold, "DOWN", "NEUTRAL")))
    return label


def make_regression_targets(close: pd.Series, high: pd.Series, low: pd.Series, horizon: int) -> pd.DataFrame:
    future_close = close.shift(-horizon)
    future_high = high.shift(-horizon).rolling(horizon).max().shift(1 - horizon)  # careful
    # Use simple horizon window max/min of future path via reverse rolling trick:
    # For research clarity: expected_high/low approximated by max/min over next h days.
    fwd_high = high[::-1].rolling(horizon).max()[::-1].shift(-horizon + 1) if False else None
    # Explicit loop-free approximation: rolling on shifted series
    # max of closes path — use high rolling forward via shift
    rh = high.iloc[::-1].rolling(horizon).max().iloc[::-1]
    rl = low.iloc[::-1].rolling(horizon).min().iloc[::-1]
    return pd.DataFrame(
        {
            "expected_return": future_close / close - 1,
            "expected_high": rh / close - 1,
            "expected_low": rl / close - 1,
        }
    )


FEATURE_COLUMNS = [
    "ret_1",
    "ret_5",
    "ret_20",
    "gap",
    "hl_range",
    "roll_high_20",
    "roll_low_20",
    "sma_20",
    "sma_50",
    "ema_12",
    "ema_26",
    "macd",
    "macd_signal",
    "macd_hist",
    "adx_14",
    "atr_14",
    "rsi_14",
    "stoch_k",
    "roc_10",
    "vol_20",
    "bb_upper",
    "bb_lower",
    "bb_width",
    "vol_sma_20",
    "rel_volume",
    "obv_slope",
    "nifty_ret_20",
    "rel_strength_20",
    "market_vol_20",
]
