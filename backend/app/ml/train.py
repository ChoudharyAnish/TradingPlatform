"""Model training, calibration, and comparison."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from app.backtesting.metrics import overfitting_warnings, prediction_metrics
from app.core.config import get_settings
from app.features.technical import FEATURE_COLUMNS

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover
    XGBClassifier = None

try:
    from lightgbm import LGBMClassifier
except Exception:  # pragma: no cover
    LGBMClassifier = None


LABELS = ["DOWN", "NEUTRAL", "UP"]


@dataclass
class TrainedModel:
    model_type: str
    pipeline: Any
    label_encoder: LabelEncoder
    feature_names: list[str]
    train_metrics: dict
    valid_metrics: dict
    test_metrics: dict
    warnings: list[str]
    calibrated: bool


def _build_estimator(model_type: str, seed: int):
    if model_type == "logistic":
        return LogisticRegression(max_iter=1000, random_state=seed)
    if model_type == "random_forest":
        return RandomForestClassifier(n_estimators=200, max_depth=6, random_state=seed, n_jobs=-1)
    if model_type == "gbm":
        return GradientBoostingClassifier(random_state=seed)
    if model_type == "xgboost":
        if XGBClassifier is None:
            raise RuntimeError("xgboost not installed")
        return XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=seed,
            objective="multi:softprob",
            num_class=3,
            eval_metric="mlogloss",
        )
    if model_type == "lightgbm":
        if LGBMClassifier is None:
            raise RuntimeError("lightgbm not installed")
        return LGBMClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=seed,
            class_weight="balanced",
        )
    raise ValueError(f"Unknown model_type={model_type}")


def train_classifier(
    train_df: pd.DataFrame,
    valid_df: pd.DataFrame,
    test_df: pd.DataFrame,
    *,
    model_type: str = "lightgbm",
    feature_names: Optional[list[str]] = None,
    calibrate: bool = True,
    method: str = "isotonic",
) -> TrainedModel:
    settings = get_settings()
    feature_names = feature_names or FEATURE_COLUMNS
    le = LabelEncoder()
    le.fit(LABELS)

    def xy(df: pd.DataFrame):
        X = df[feature_names].astype(float).replace([np.inf, -np.inf], np.nan).fillna(0.0)
        y = le.transform(df["target"].astype(str))
        return X, y

    X_tr, y_tr = xy(train_df)
    X_va, y_va = xy(valid_df)
    X_te, y_te = xy(test_df)

    est = _build_estimator(model_type, settings.random_seed)
    pipe: Any = Pipeline([("scaler", StandardScaler()), ("clf", est)])
    pipe.fit(X_tr, y_tr)

    calibrated = False
    if calibrate and len(np.unique(y_va)) > 1 and len(X_va) >= 30:
        # Calibrate on validation fold only (not test)
        try:
            calib = CalibratedClassifierCV(pipe, method=method if method in {"isotonic", "sigmoid"} else "sigmoid", cv="prefit")
            # sklearn >=1.4 uses cv='prefit' differently; fallback: fit fresh with cv
            calib.fit(X_va, y_va)
            model = calib
            calibrated = True
        except Exception:
            model = pipe
    else:
        model = pipe

    def eval_split(X, y):
        pred = model.predict(X)
        proba = model.predict_proba(X)
        y_lbl = le.inverse_transform(y)
        y_hat = le.inverse_transform(pred)
        return prediction_metrics(y_lbl, y_hat, proba, labels=list(le.classes_))

    train_m = eval_split(X_tr, y_tr)
    valid_m = eval_split(X_va, y_va)
    test_m = eval_split(X_te, y_te)
    warns = overfitting_warnings(train_m, test_m, n_samples=len(X_te), n_params=len(feature_names))
    if abs((test_m.get("accuracy") or 0) - (valid_m.get("accuracy") or 0)) > 0.12:
        warns.append("UNSTABLE_PERFORMANCE")

    return TrainedModel(
        model_type=model_type,
        pipeline=model,
        label_encoder=le,
        feature_names=feature_names,
        train_metrics=train_m,
        valid_metrics=valid_m,
        test_metrics=test_m,
        warnings=sorted(set(warns)),
        calibrated=calibrated,
    )


def save_model(model: TrainedModel, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)


def load_model(path: Path) -> TrainedModel:
    return joblib.load(path)


def predict_proba_row(model: TrainedModel, features: dict) -> dict:
    X = pd.DataFrame([{c: float(features.get(c, 0.0) or 0.0) for c in model.feature_names}])
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    proba = model.pipeline.predict_proba(X)[0]
    classes = list(model.label_encoder.classes_)
    mapping = {cls: float(p) for cls, p in zip(classes, proba)}
    direction = max(mapping, key=mapping.get)
    return {"direction": direction, "probability": mapping[direction], "proba": mapping}


def feature_contributions(model: TrainedModel, features: dict, top_k: int = 8) -> list[dict]:
    """Simple signed contribution via feature * coef or impurity importance * value sign."""
    vals = np.array([float(features.get(c, 0.0) or 0.0) for c in model.feature_names])
    names = model.feature_names
    importances = None
    clf = model.pipeline
    # unwrap calibrated / pipeline
    base = clf
    if hasattr(clf, "calibrated_classifiers_"):
        base = clf.calibrated_classifiers_[0].estimator
    if hasattr(base, "named_steps"):
        est = base.named_steps.get("clf", base)
    else:
        est = base
    if hasattr(est, "feature_importances_"):
        importances = np.asarray(est.feature_importances_, dtype=float)
        scores = importances * np.sign(vals)
    elif hasattr(est, "coef_"):
        # use UP class coef if multiclass
        coef = np.asarray(est.coef_)
        if coef.ndim == 2:
            # pick UP index if present
            try:
                up_idx = list(model.label_encoder.classes_).index("UP")
                coef = coef[up_idx]
            except Exception:
                coef = coef[0]
        scores = coef * vals
    else:
        scores = vals

    order = np.argsort(np.abs(scores))[::-1][:top_k]
    out = []
    for i in order:
        out.append(
            {
                "feature": names[i],
                "value": float(vals[i]),
                "contribution": float(scores[i]),
                "direction": "positive" if scores[i] >= 0 else "negative",
            }
        )
    return out
