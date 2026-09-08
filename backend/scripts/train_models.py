"""Train and compare multiple models; register best validated candidate honestly."""

from __future__ import annotations

from datetime import date

import pandas as pd

from app.backtesting.walk_forward import chronological_split
from app.core.logging import get_logger, setup_logging
from app.db.session import SessionLocal
from app.features.technical import FEATURE_COLUMNS, compute_technical_features, make_classification_target
from app.ml.registry.store import register_model
from app.ml.train import train_classifier
from app.services.market import load_universe, prices_frame

setup_logging(True)
logger = get_logger(__name__)

MODEL_TYPES = ["logistic", "random_forest", "gbm", "xgboost", "lightgbm"]


def main():
    db = SessionLocal()
    symbols = [s for s in load_universe().get("universe", {}).get("symbols", []) if not s.startswith("NIFTY")]
    idx = prices_frame(db, "NIFTY_50")
    frames = []
    for sym in symbols:
        df = prices_frame(db, sym)
        if df.empty:
            continue
        index_close = None
        if not idx.empty:
            merged = df.merge(idx[["trade_date", "adjusted_close"]], on="trade_date", how="left", suffixes=("", "_idx"))
            index_close = merged["adjusted_close_idx"]
        feats = compute_technical_features(df, index_close=index_close)
        feats["target"] = make_classification_target(df["adjusted_close"], horizon=5)
        frames.append(feats)
    data = pd.concat(frames, ignore_index=True).dropna(subset=FEATURE_COLUMNS + ["target"])
    data = data[data["target"].isin(["UP", "DOWN", "NEUTRAL"])]
    split = chronological_split(sorted(data["trade_date"].unique().tolist()))
    train = data[(data["trade_date"] >= split.train_start) & (data["trade_date"] <= split.train_end)]
    valid = data[(data["trade_date"] >= split.valid_start) & (data["trade_date"] <= split.valid_end)]
    test = data[(data["trade_date"] >= split.test_start) & (data["trade_date"] <= split.test_end)]

    results = []
    for mt in MODEL_TYPES:
        try:
            model = train_classifier(train, valid, test, model_type=mt, calibrate=True)
        except Exception as exc:
            logger.warning("train_failed", model=mt, error=str(exc))
            continue
        status = "VALIDATED"
        if any(w in model.warnings for w in ("OVERFITTING_RISK", "POOR_OUT_OF_SAMPLE_PERFORMANCE")):
            status = "EXPERIMENTAL"
        run = register_model(
            db,
            model,
            version=f"{mt}-wf1",
            dataset_version="sample-v1",
            splits={
                "train_start": split.train_start,
                "train_end": split.train_end,
                "valid_start": split.valid_start,
                "valid_end": split.valid_end,
                "test_start": split.test_start,
                "test_end": split.test_end,
            },
            status=status,
        )
        results.append({"model_id": run.model_id, "test": model.test_metrics, "warnings": model.warnings, "status": status})
        logger.info("trained", **results[-1])

    print(pd.DataFrame(results).to_string(index=False))
    db.close()


if __name__ == "__main__":
    main()
