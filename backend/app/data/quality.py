"""Data quality checks for OHLCV series."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd


@dataclass
class DQIssue:
    check_type: str
    severity: str
    message: str
    details: dict


def check_ohlcv(df: pd.DataFrame, symbol: str) -> list[DQIssue]:
    issues: list[DQIssue] = []
    if df.empty:
        return [DQIssue("missing_prices", "ERROR", f"No prices for {symbol}", {})]

    required = {"trade_date", "open", "high", "low", "close", "adjusted_close", "volume"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        issues.append(
            DQIssue("schema", "ERROR", f"Missing columns {missing_cols}", {"symbol": symbol})
        )
        return issues

    # duplicates
    dup = df["trade_date"].duplicated().sum()
    if dup:
        issues.append(
            DQIssue("duplicate_records", "ERROR", f"{dup} duplicate dates", {"symbol": symbol})
        )

    # impossible OHLC
    bad = df[
        (df["high"] < df["low"])
        | (df["high"] < df["open"])
        | (df["high"] < df["close"])
        | (df["low"] > df["open"])
        | (df["low"] > df["close"])
        | (df["open"] <= 0)
        | (df["close"] <= 0)
    ]
    if len(bad):
        issues.append(
            DQIssue(
                "impossible_ohlc",
                "ERROR",
                f"{len(bad)} impossible OHLC rows",
                {"symbol": symbol, "sample_dates": bad["trade_date"].astype(str).head(5).tolist()},
            )
        )

    # volume anomalies
    if df["volume"].mean() > 0:
        spike = df[df["volume"] > df["volume"].median() * 50]
        if len(spike):
            issues.append(
                DQIssue(
                    "abnormal_volume",
                    "WARN",
                    f"{len(spike)} abnormal volume spikes",
                    {"symbol": symbol},
                )
            )

    # missing calendar gaps (weekdays only heuristic)
    dates = sorted(pd.to_datetime(df["trade_date"]).dt.date.tolist())
    if len(dates) >= 2:
        gaps = []
        for a, b in zip(dates[:-1], dates[1:]):
            delta = (b - a).days
            if delta > 5:  # ignore weekends/short holidays
                gaps.append({"from": str(a), "to": str(b), "days": delta})
        if gaps:
            issues.append(
                DQIssue(
                    "missing_dates",
                    "WARN",
                    f"{len(gaps)} large gaps",
                    {"symbol": symbol, "gaps": gaps[:10]},
                )
            )

    # stale data
    last = dates[-1]
    if (date.today() - last).days > 10:
        issues.append(
            DQIssue(
                "stale_data",
                "WARN",
                f"Last bar {last} is stale",
                {"symbol": symbol, "last": str(last)},
            )
        )

    return issues
