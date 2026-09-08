"""Trading and prediction performance metrics."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
    average_precision_score,
)


def prediction_metrics(y_true, y_pred, y_proba=None, labels=None) -> dict:
    labels = labels or ["DOWN", "NEUTRAL", "UP"]
    out = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "n_samples": int(len(y_true)),
    }
    if y_proba is not None:
        try:
            out["log_loss"] = float(log_loss(y_true, y_proba, labels=labels))
        except Exception:
            out["log_loss"] = None
        # binary UP vs rest for ROC if possible
        try:
            y_bin = np.array([1 if y == "UP" else 0 for y in y_true])
            if y_proba.ndim == 2 and "UP" in labels:
                up_idx = labels.index("UP")
                out["roc_auc_up"] = float(roc_auc_score(y_bin, y_proba[:, up_idx]))
                out["pr_auc_up"] = float(average_precision_score(y_bin, y_proba[:, up_idx]))
                out["brier_up"] = float(brier_score_loss(y_bin, y_proba[:, up_idx]))
        except Exception:
            pass
    return out


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = (equity - peak) / peak
    return float(dd.min()) if len(dd) else 0.0


def trading_metrics(
    equity_curve: list[dict],
    trades: list[dict],
    *,
    risk_free: float = 0.06,
    periods_per_year: int = 252,
) -> dict:
    if not equity_curve:
        return {"total_return": 0.0, "n_trades": 0}
    eq = pd.Series([e["equity"] for e in equity_curve], dtype=float)
    rets = eq.pct_change().dropna()
    total_return = float(eq.iloc[-1] / eq.iloc[0] - 1)
    n_days = max(len(eq) - 1, 1)
    cagr = float((eq.iloc[-1] / eq.iloc[0]) ** (periods_per_year / n_days) - 1) if eq.iloc[0] > 0 else 0.0
    vol = float(rets.std() * math.sqrt(periods_per_year)) if len(rets) else 0.0
    sharpe = float((rets.mean() * periods_per_year - risk_free) / vol) if vol > 0 else 0.0
    downside = rets[rets < 0]
    down_vol = float(downside.std() * math.sqrt(periods_per_year)) if len(downside) else 0.0
    sortino = float((rets.mean() * periods_per_year - risk_free) / down_vol) if down_vol > 0 else 0.0
    mdd = max_drawdown(eq)
    calmar = float(cagr / abs(mdd)) if mdd < 0 else 0.0

    pnls = [float(t.get("pnl") or 0) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    win_rate = len(wins) / len(pnls) if pnls else 0.0
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0
    expectancy = float(np.mean(pnls)) if pnls else 0.0
    hold = []
    for t in trades:
        if t.get("entry_date") and t.get("exit_date"):
            hold.append((pd.to_datetime(t["exit_date"]) - pd.to_datetime(t["entry_date"])).days)
    avg_hold = float(np.mean(hold)) if hold else 0.0

    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": mdd,
        "calmar": calmar,
        "win_rate": win_rate,
        "profit_factor": profit_factor if math.isfinite(profit_factor) else None,
        "average_win": avg_win,
        "average_loss": avg_loss,
        "expectancy": expectancy,
        "n_trades": len(pnls),
        "average_holding_period": avg_hold,
        "volatility": vol,
    }


def overfitting_warnings(
    train_metrics: dict,
    test_metrics: dict,
    *,
    n_samples: int,
    n_params: int = 10,
) -> list[str]:
    warnings: list[str] = []
    if n_samples < 200:
        warnings.append("LOW_SAMPLE_SIZE")
    train_acc = train_metrics.get("accuracy") or 0
    test_acc = test_metrics.get("accuracy") or 0
    if train_acc - test_acc > 0.15:
        warnings.append("OVERFITTING_RISK")
    if (test_metrics.get("sharpe") or 0) < 0:
        warnings.append("POOR_OUT_OF_SAMPLE_PERFORMANCE")
    if abs(test_metrics.get("max_drawdown") or 0) > 0.25:
        warnings.append("HIGH_DRAWDOWN")
    if n_params > max(5, n_samples // 20):
        warnings.append("EXCESSIVE_PARAMETER_OPTIMIZATION")
    return warnings
