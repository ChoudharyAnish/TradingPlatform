"""Prediction / screener orchestration."""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.features.technical import FEATURE_COLUMNS
from app.ml.ensemble.combiner import EnsemblePredictor
from app.ml.registry.store import get_production_model
from app.models import MarketRegimeSnapshot, Stock, TechnicalFeature
from app.services.market import prices_frame
from app.signals.engine import build_signal, signal_to_dict


def latest_features(db: Session, stock_id: int) -> Optional[dict]:
    row = (
        db.query(TechnicalFeature)
        .filter_by(stock_id=stock_id)
        .order_by(TechnicalFeature.trade_date.desc())
        .first()
    )
    return row.features if row else None


def current_regime(db: Session) -> tuple[str, date | None]:
    snap = db.query(MarketRegimeSnapshot).order_by(MarketRegimeSnapshot.as_of_date.desc()).first()
    if snap:
        return snap.regime, snap.as_of_date
    return "SIDEWAYS", None


def generate_predictions(db: Session, symbols: Optional[list[str]] = None, horizon: int = 5) -> list[dict]:
    settings = get_settings()
    loaded = get_production_model(db)
    model = loaded[1] if loaded else None
    run = loaded[0] if loaded else None
    ensemble = EnsemblePredictor(technical=model)
    regime, _ = current_regime(db)
    q = db.query(Stock).filter(Stock.is_active.is_(True), Stock.instrument_type == "EQUITY")
    if symbols:
        q = q.filter(Stock.symbol.in_(symbols))
    out = []
    equity = settings.initial_capital
    for stock in q.all():
        feats = latest_features(db, stock.id)
        if not feats:
            continue
        # ensure keys
        clean = {k: feats.get(k) for k in FEATURE_COLUMNS}
        pred = ensemble.predict(stock.symbol, clean, regime=regime)
        px = float(feats.get("close") or 0)
        if px <= 0:
            df = prices_frame(db, stock.symbol)
            if df.empty:
                continue
            px = float(df.iloc[-1]["close"])
        atr = float(feats.get("atr_14") or 0) * px
        sig = build_signal(
            pred,
            price=px,
            atr=max(atr, px * 0.01),
            equity=equity,
            horizon=horizon,
            regime=regime,
            model_version=run.model_id if run else "heuristic-v0",
            result_channel="PAPER" if run and run.status in {"VALIDATED", "PAPER_TRADING"} else "BACKTEST",
        )
        payload = signal_to_dict(sig)
        payload["direction"] = pred.direction
        payload["proba"] = pred.proba
        out.append(payload)
    return out


def screen(db: Session, **filters) -> list[dict]:
    preds = generate_predictions(db)
    min_p = filters.get("min_probability", 0.7)
    min_er = filters.get("min_expected_return", 0.02)
    max_risk = filters.get("max_risk_score", 0.4)
    sector = filters.get("sector")
    max_rsi = filters.get("max_rsi")
    results = []
    for p in preds:
        if p["probability"] < min_p:
            continue
        if p["expected_return"] < min_er:
            continue
        if p["risk_score"] > max_risk:
            continue
        stock = db.query(Stock).filter_by(symbol=p["symbol"]).first()
        if sector and stock and stock.sector and stock.sector.code != sector:
            continue
        feats = latest_features(db, stock.id) if stock else None
        if max_rsi is not None and feats and (feats.get("rsi_14") or 0) > max_rsi:
            continue
        results.append(p)
    return sorted(results, key=lambda x: x["probability"], reverse=True)
