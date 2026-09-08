"""Seed DB from sample CSVs, compute features, train a baseline model, run example backtest."""

from __future__ import annotations

from datetime import date

from app.backtesting.engine import EventDrivenBacktester
from app.backtesting.walk_forward import chronological_split
from app.core.logging import get_logger, setup_logging
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.features.technical import FEATURE_COLUMNS, compute_technical_features, make_classification_target
from app.ml.registry.store import register_model
from app.ml.train import train_classifier
from app.models import Backtest
from app.services.market import (
    compute_and_store_features,
    ingest_symbol,
    load_universe,
    prices_frame,
    update_market_regime,
)
from decimal import Decimal

setup_logging(True)
logger = get_logger(__name__)


def main():
    settings = get_settings()
    db = SessionLocal()
    uni = load_universe()
    symbols = uni.get("universe", {}).get("symbols", [])
    start, end = date(2022, 1, 1), date(2025, 12, 31)
    for sym in symbols:
        n = ingest_symbol(db, sym, start, end)
        logger.info("seed_ingest", symbol=sym, inserted=n)
        compute_and_store_features(db, sym)
    update_market_regime(db)

    # Build training frame across equities
    frames = []
    idx = prices_frame(db, "NIFTY_50")
    for sym in symbols:
        if sym.startswith("NIFTY"):
            continue
        df = prices_frame(db, sym)
        if df.empty:
            continue
        index_close = None
        if not idx.empty:
            merged = df.merge(idx[["trade_date", "adjusted_close"]], on="trade_date", how="left", suffixes=("", "_idx"))
            index_close = merged["adjusted_close_idx"]
        feats = compute_technical_features(df, index_close=index_close)
        feats["target"] = make_classification_target(df["adjusted_close"], horizon=5)
        feats["symbol"] = sym
        frames.append(feats)

    import pandas as pd

    data = pd.concat(frames, ignore_index=True).dropna(subset=FEATURE_COLUMNS + ["target"])
    # drop last horizon rows already handled by dropna on target where future missing -> NEUTRAL/NaN
    data = data[data["target"].isin(["UP", "DOWN", "NEUTRAL"])]
    dates = sorted(data["trade_date"].unique().tolist())
    split = chronological_split(dates)
    train = data[(data["trade_date"] >= split.train_start) & (data["trade_date"] <= split.train_end)]
    valid = data[(data["trade_date"] >= split.valid_start) & (data["trade_date"] <= split.valid_end)]
    test = data[(data["trade_date"] >= split.test_start) & (data["trade_date"] <= split.test_end)]

    model = train_classifier(train, valid, test, model_type="random_forest", calibrate=True)
    run = register_model(
        db,
        model,
        version="v1",
        dataset_version="sample-v1",
        splits={
            "train_start": split.train_start,
            "train_end": split.train_end,
            "valid_start": split.valid_start,
            "valid_end": split.valid_end,
            "test_start": split.test_start,
            "test_end": split.test_end,
        },
        status="VALIDATED" if "OVERFITTING_RISK" not in model.warnings else "EXPERIMENTAL",
    )
    logger.info("model_registered", model_id=run.model_id, warnings=model.warnings, test=model.test_metrics)

    # Example backtest
    prices = {s: prices_frame(db, s) for s in symbols}
    prices = {k: v for k, v in prices.items() if not v.empty}

    def signal_fn(symbol, d, row):
        hist = prices[symbol]
        hist = hist[hist["trade_date"] <= d]
        if len(hist) < 6:
            return None
        c = hist["close"].astype(float)
        ret5 = float(c.iloc[-1] / c.iloc[-6] - 1)
        if ret5 > 0.015:
            px = float(row["close"])
            return {"action": "BUY", "stop": px * 0.97, "target": px * 1.05, "sector": "UNKNOWN"}
        return {"action": "HOLD"}

    engine = EventDrivenBacktester(prices, initial_capital=settings.initial_capital)
    eq_syms = [s for s in symbols if not s.startswith("NIFTY")]
    result = engine.run(date(2024, 1, 1), date(2025, 6, 30), signal_fn, symbols=eq_syms)
    bt = Backtest(
        name="seed_example_momentum",
        strategy="momentum_ret5",
        universe={"symbols": eq_syms},
        start_date=date(2024, 1, 1),
        end_date=date(2025, 6, 30),
        initial_capital=Decimal(str(settings.initial_capital)),
        config=result.config,
        metrics=result.metrics,
        equity_curve=result.equity_curve,
        drawdown_curve=result.drawdown_curve,
        monthly_returns=result.monthly_returns,
        warnings=result.warnings,
        benchmark_metrics=result.benchmark_metrics,
        result_channel="BACKTEST",
    )
    db.add(bt)
    db.commit()
    logger.info("backtest_saved", metrics=result.metrics, warnings=result.warnings)
    model_id = run.model_id
    metrics = dict(result.metrics)
    db.close()
    print("Seed complete. Model:", model_id, "Backtest metrics:", metrics)


if __name__ == "__main__":
    main()
