"""Run a standalone example backtest and print metrics."""

from datetime import date

from app.backtesting.engine import EventDrivenBacktester
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.market import load_universe, prices_frame


def main():
    db = SessionLocal()
    symbols = load_universe().get("universe", {}).get("symbols", [])
    prices = {s: prices_frame(db, s) for s in symbols}
    prices = {k: v for k, v in prices.items() if not v.empty}
    eq = [s for s in prices if not s.startswith("NIFTY")]

    def signal_fn(symbol, d, row):
        hist = prices[symbol]
        hist = hist[hist["trade_date"] <= d]
        if len(hist) < 21:
            return None
        c = hist["close"].astype(float)
        mom = float(c.iloc[-1] / c.iloc[-21] - 1)
        if mom > 0.03:
            px = float(row["close"])
            return {"action": "BUY", "stop": px * 0.96, "target": px * 1.08}
        return {"action": "HOLD"}

    result = EventDrivenBacktester(prices).run(date(2024, 1, 1), date(2025, 12, 31), signal_fn, symbols=eq)
    print("result_channel=BACKTEST")
    print("disclaimer: Backtested results are not guarantees of future performance.")
    print(result.metrics)
    print("benchmark", result.benchmark_metrics)
    print("warnings", result.warnings)
    db.close()


if __name__ == "__main__":
    main()
