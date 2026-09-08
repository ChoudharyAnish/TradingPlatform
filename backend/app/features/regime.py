"""Market regime detection from index-level features."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class RegimeResult:
    regime: str
    features: dict


def detect_regime(index_ohlcv: pd.DataFrame) -> RegimeResult:
    df = index_ohlcv.sort_values("trade_date").copy()
    c = df["adjusted_close"].astype(float)
    v = df["volume"].astype(float)
    ret_20 = c.pct_change(20).iloc[-1]
    vol_20 = c.pct_change().rolling(20).std().iloc[-1]
    vol_median = c.pct_change().rolling(20).std().median()
    mom = c.pct_change(60).iloc[-1]
    vol_ratio = float(vol_20 / vol_median) if vol_median and not np.isnan(vol_median) else 1.0
    rel_vol = float(v.iloc[-1] / (v.rolling(20).mean().iloc[-1] + 1e-9))

    features = {
        "ret_20": float(ret_20) if pd.notna(ret_20) else 0.0,
        "vol_20": float(vol_20) if pd.notna(vol_20) else 0.0,
        "vol_ratio": vol_ratio,
        "momentum_60": float(mom) if pd.notna(mom) else 0.0,
        "rel_volume": rel_vol,
    }

    if vol_ratio > 1.5:
        regime = "HIGH_VOLATILITY"
    elif vol_ratio < 0.7:
        regime = "LOW_VOLATILITY"
    elif features["ret_20"] > 0.03 and features["momentum_60"] > 0:
        regime = "BULL"
    elif features["ret_20"] < -0.03 and features["momentum_60"] < 0:
        regime = "BEAR"
    else:
        regime = "SIDEWAYS"

    return RegimeResult(regime=regime, features=features)
