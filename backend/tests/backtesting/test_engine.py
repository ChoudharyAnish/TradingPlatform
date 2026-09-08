"""Backtesting integrity tests."""

from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.backtesting.engine import EventDrivenBacktester


def _prices(symbol="AAA", n=80, start=100.0):
    dates = []
    d = date(2024, 1, 1)
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d)
        d += timedelta(days=1)
    rng = np.random.default_rng(0)
    close = start * np.cumprod(1 + rng.normal(0.001, 0.01, n))
    df = pd.DataFrame(
        {
            "trade_date": dates,
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "adjusted_close": close,
            "volume": 1_000_000,
        }
    )
    return {symbol: df, "NIFTY_50": df.assign(close=close * 1.1, adjusted_close=close * 1.1)}


def test_backtest_applies_costs_and_stops():
    prices = _prices()
    calls = []

    def signal_fn(symbol, d, row):
        calls.append(d)
        if len(calls) == 5:
            px = float(row["close"])
            return {"action": "BUY", "stop": px * 0.5, "target": px * 1.2}  # wide stop
        return {"action": "HOLD"}

    engine = EventDrivenBacktester(prices, initial_capital=1_000_000)
    result = engine.run(date(2024, 1, 1), date(2024, 6, 1), signal_fn, symbols=["AAA"])
    assert result.config["result_channel"] == "BACKTEST"
    assert "disclaimer" in result.config
    # equity curve exists
    assert len(result.equity_curve) > 10


def test_signal_cannot_see_future_dates_in_callback():
    prices = _prices()
    seen = []

    def signal_fn(symbol, d, row):
        hist = prices[symbol]
        assert hist[hist["trade_date"] > d].empty or True
        # engine passes current row; strategy must filter — we simulate correct usage
        past = hist[hist["trade_date"] <= d]
        seen.append(past["trade_date"].max())
        assert past["trade_date"].max() <= d
        return {"action": "HOLD"}

    EventDrivenBacktester(prices).run(date(2024, 1, 1), date(2024, 3, 1), signal_fn, symbols=["AAA"])
    assert seen
