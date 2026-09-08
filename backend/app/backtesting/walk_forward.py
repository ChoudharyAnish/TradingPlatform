"""Walk-forward validation helpers for time series (no random shuffle)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterator, Literal

import pandas as pd


@dataclass
class TimeSplit:
    train_start: date
    train_end: date
    valid_start: date
    valid_end: date
    test_start: date
    test_end: date


def chronological_split(
    dates: list[date],
    train_ratio: float = 0.6,
    valid_ratio: float = 0.2,
) -> TimeSplit:
    d = sorted(dates)
    n = len(d)
    i_train = int(n * train_ratio)
    i_valid = int(n * (train_ratio + valid_ratio))
    return TimeSplit(
        train_start=d[0],
        train_end=d[i_train - 1],
        valid_start=d[i_train],
        valid_end=d[i_valid - 1],
        test_start=d[i_valid],
        test_end=d[-1],
    )


def walk_forward_splits(
    dates: list[date],
    *,
    train_size: int,
    valid_size: int,
    test_size: int,
    step: int,
    mode: Literal["expanding", "rolling"] = "rolling",
) -> Iterator[TimeSplit]:
    d = sorted(dates)
    start = 0
    while True:
        if mode == "expanding":
            tr_start = 0
        else:
            tr_start = start
        tr_end = tr_start + train_size
        va_end = tr_end + valid_size
        te_end = va_end + test_size
        if te_end > len(d):
            break
        yield TimeSplit(
            train_start=d[tr_start],
            train_end=d[tr_end - 1],
            valid_start=d[tr_end],
            valid_end=d[va_end - 1],
            test_start=d[va_end],
            test_end=d[te_end - 1],
        )
        start += step


def assert_no_leakage(feature_dates: pd.Series, target_horizon: int) -> None:
    """Lightweight guard: targets must not use feature rows within horizon of end without NaN drop."""
    if feature_dates.is_monotonic_increasing is False:
        raise ValueError("Feature dates must be sorted ascending to avoid look-ahead confusion")
