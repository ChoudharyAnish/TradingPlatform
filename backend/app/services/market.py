"""Ingestion and query services."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml
from sqlalchemy.orm import Session
# pandas used throughout for frames / null checks

from app.core.config import get_settings
from app.core.logging import get_logger
from app.data.providers import get_historical_provider
from app.data.quality import check_ohlcv
from app.features.regime import detect_regime
from app.features.technical import FEATURE_SET_VERSION, compute_technical_features
from app.models import (
    DataQualityLog,
    Exchange,
    HistoricalPrice,
    MarketRegimeSnapshot,
    Sector,
    Stock,
    TechnicalFeature,
)

logger = get_logger(__name__)


def ensure_reference_data(db: Session) -> None:
    if not db.query(Exchange).filter_by(code="NSE").first():
        db.add(Exchange(code="NSE", name="National Stock Exchange of India"))
    if not db.query(Exchange).filter_by(code="BSE").first():
        db.add(Exchange(code="BSE", name="BSE Limited"))
    defaults = [("IT", "Information Technology"), ("BANK", "Banks"), ("ENERGY", "Energy"), ("INDEX", "Index")]
    for code, name in defaults:
        if not db.query(Sector).filter_by(code=code).first():
            db.add(Sector(code=code, name=name))
    db.commit()


def load_universe() -> dict:
    settings = get_settings()
    path = settings.resolve_path(settings.universe_config)
    if not path.exists():
        path = Path(__file__).resolve().parents[3] / "config" / "universe.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


SECTOR_MAP = {
    "TCS": "IT",
    "INFY": "IT",
    "HDFCBANK": "BANK",
    "ICICIBANK": "BANK",
    "SBIN": "BANK",
    "KOTAKBANK": "BANK",
    "RELIANCE": "ENERGY",
    "NIFTY_50": "INDEX",
    "NIFTY_BANK": "INDEX",
}


def upsert_stock(db: Session, symbol: str, name: Optional[str] = None) -> Stock:
    ensure_reference_data(db)
    exch = db.query(Exchange).filter_by(code="NSE").one()
    sector_code = SECTOR_MAP.get(symbol, "IT" if symbol.endswith("Y") else "ENERGY")
    sector = db.query(Sector).filter_by(code=sector_code).one()
    stock = db.query(Stock).filter_by(symbol=symbol, exchange_id=exch.id).first()
    instrument = "INDEX" if symbol.startswith("NIFTY") else "EQUITY"
    if not stock:
        stock = Stock(
            symbol=symbol,
            name=name or symbol,
            exchange_id=exch.id,
            sector_id=sector.id,
            instrument_type=instrument,
            is_liquid=True,
        )
        db.add(stock)
        db.commit()
        db.refresh(stock)
    return stock


def ingest_symbol(db: Session, symbol: str, start: date, end: date) -> int:
    provider = get_historical_provider()
    df = provider.get_ohlcv(symbol, start, end)
    issues = check_ohlcv(df, symbol)
    stock = upsert_stock(db, symbol)
    for issue in issues:
        db.add(
            DataQualityLog(
                stock_id=stock.id,
                check_type=issue.check_type,
                severity=issue.severity,
                message=issue.message,
                details=issue.details,
            )
        )
    if df.empty:
        db.commit()
        return 0

    # liquidity filter for equities
    settings = get_settings()
    if not symbol.startswith("NIFTY"):
        avg_vol = float(df["volume"].tail(60).mean()) if len(df) else 0
        stock.is_liquid = avg_vol >= settings.min_avg_daily_volume
        stock.is_active = len(df) >= settings.min_price_history_days or True  # sample may be shorter

    count = 0
    for row in df.itertuples():
        existing = (
            db.query(HistoricalPrice)
            .filter_by(stock_id=stock.id, trade_date=row.trade_date)
            .first()
        )
        vals = dict(
            open=Decimal(str(row.open)),
            high=Decimal(str(row.high)),
            low=Decimal(str(row.low)),
            close=Decimal(str(row.close)),
            adjusted_close=Decimal(str(getattr(row, "adjusted_close", row.close))),
            volume=int(row.volume),
            source=getattr(row, "source", "unknown"),
            as_of_ts=datetime.now(timezone.utc),
        )
        if existing:
            for k, v in vals.items():
                setattr(existing, k, v)
        else:
            db.add(HistoricalPrice(stock_id=stock.id, trade_date=row.trade_date, **vals))
            count += 1
    db.commit()
    logger.info("ingested", symbol=symbol, rows=count)
    return count


def prices_frame(db: Session, symbol: str) -> pd.DataFrame:
    stock = db.query(Stock).filter_by(symbol=symbol).first()
    if not stock:
        return pd.DataFrame()
    rows = (
        db.query(HistoricalPrice)
        .filter_by(stock_id=stock.id)
        .order_by(HistoricalPrice.trade_date)
        .all()
    )
    return pd.DataFrame(
        [
            {
                "trade_date": r.trade_date,
                "open": float(r.open),
                "high": float(r.high),
                "low": float(r.low),
                "close": float(r.close),
                "adjusted_close": float(r.adjusted_close),
                "volume": int(r.volume),
            }
            for r in rows
        ]
    )


def compute_and_store_features(db: Session, symbol: str) -> int:
    df = prices_frame(db, symbol)
    if df.empty:
        return 0
    idx = prices_frame(db, "NIFTY_50")
    index_close = None
    if not idx.empty:
        merged = df.merge(idx[["trade_date", "adjusted_close"]], on="trade_date", how="left", suffixes=("", "_idx"))
        index_close = merged["adjusted_close_idx"]
    feats = compute_technical_features(df, index_close=index_close)
    stock = db.query(Stock).filter_by(symbol=symbol).one()
    n = 0
    for row in feats.itertuples(index=False):
        feature_dict = {c: (None if pd.isna(getattr(row, c)) else float(getattr(row, c))) for c in feats.columns if c != "trade_date"}
        existing = (
            db.query(TechnicalFeature)
            .filter_by(stock_id=stock.id, trade_date=row.trade_date, feature_set_version=FEATURE_SET_VERSION)
            .first()
        )
        if existing:
            existing.features = feature_dict
        else:
            db.add(
                TechnicalFeature(
                    stock_id=stock.id,
                    trade_date=row.trade_date,
                    feature_set_version=FEATURE_SET_VERSION,
                    features=feature_dict,
                )
            )
            n += 1
    db.commit()
    return n


def update_market_regime(db: Session) -> Optional[MarketRegimeSnapshot]:
    df = prices_frame(db, "NIFTY_50")
    if len(df) < 60:
        return None
    result = detect_regime(df)
    as_of = df["trade_date"].iloc[-1]
    snap = db.query(MarketRegimeSnapshot).filter_by(as_of_date=as_of).first()
    if snap:
        snap.regime = result.regime
        snap.features = result.features
    else:
        snap = MarketRegimeSnapshot(as_of_date=as_of, regime=result.regime, features=result.features)
        db.add(snap)
    db.commit()
    db.refresh(snap)
    return snap
