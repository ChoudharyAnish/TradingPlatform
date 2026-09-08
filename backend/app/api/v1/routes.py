from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.backtesting.engine import EventDrivenBacktester
from app.db.session import get_db
from app.models import Backtest, BacktestTrade, DataQualityLog, ModelRun, Stock
from app.schemas.api import (
    BacktestCreate,
    BacktestOut,
    HealthOut,
    ModelOut,
    PortfolioOut,
    RegimeOut,
    ScreenerQuery,
    StockOut,
)
from app.core.config import get_settings
from app.services.market import prices_frame, update_market_regime
from app.services.predictions import generate_predictions, screen
from app.portfolio.paper import PaperBroker, PaperOrder

router = APIRouter()

# process-local paper account for demo
_paper = PaperBroker()


@router.get("/health", response_model=HealthOut)
def health():
    s = get_settings()
    return HealthOut(status="ok", app=s.app_name, env=s.app_env)


@router.get("/stocks", response_model=list[StockOut])
def list_stocks(db: Session = Depends(get_db)):
    return db.query(Stock).order_by(Stock.symbol).all()


@router.get("/stocks/{symbol}", response_model=StockOut)
def get_stock(symbol: str, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter_by(symbol=symbol.upper()).first()
    if not stock:
        raise HTTPException(404, "Stock not found")
    return stock


@router.get("/stocks/{symbol}/prices")
def get_prices(symbol: str, db: Session = Depends(get_db)):
    df = prices_frame(db, symbol.upper())
    if df.empty:
        raise HTTPException(404, "No prices")
    return {
        "symbol": symbol.upper(),
        "bars": df.assign(trade_date=df["trade_date"].astype(str)).to_dict(orient="records"),
        "result_channel": "HISTORICAL",
    }


@router.get("/predictions")
def predictions(
    symbol: str | None = None,
    horizon: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    symbols = [symbol.upper()] if symbol else None
    data = generate_predictions(db, symbols=symbols, horizon=horizon)
    return {
        "items": data,
        "result_channel": "PAPER",
        "disclaimer": "Predictions are probabilistic. Not investment advice.",
    }


@router.get("/signals")
def signals(db: Session = Depends(get_db)):
    data = generate_predictions(db)
    buys = [d for d in data if "BUY" in d["signal"]]
    sells = [d for d in data if "SELL" in d["signal"]]
    return {
        "top": sorted(buys, key=lambda x: x["probability"], reverse=True)[:10],
        "worst": sorted(sells, key=lambda x: x["probability"], reverse=True)[:10],
        "all": data,
        "result_channel": "PAPER",
        "disclaimer": "Signals are research outputs for paper trading / analysis only.",
    }


@router.post("/screener")
def screener(q: ScreenerQuery, db: Session = Depends(get_db)):
    items = screen(db, **q.model_dump())
    return {"items": items, "result_channel": "PAPER", "filters": q.model_dump()}


@router.get("/market/regime", response_model=RegimeOut)
def market_regime(db: Session = Depends(get_db)):
    snap = update_market_regime(db)
    if not snap:
        raise HTTPException(404, "Insufficient index history for regime detection")
    return snap


@router.get("/models", response_model=list[ModelOut])
def models(db: Session = Depends(get_db)):
    return db.query(ModelRun).order_by(ModelRun.training_date.desc()).all()


@router.get("/performance")
def performance(db: Session = Depends(get_db)):
    latest = db.query(Backtest).order_by(Backtest.created_at.desc()).first()
    models = db.query(ModelRun).order_by(ModelRun.training_date.desc()).limit(5).all()
    return {
        "latest_backtest": None
        if not latest
        else {
            "id": latest.id,
            "name": latest.name,
            "metrics": latest.metrics,
            "benchmark_metrics": latest.benchmark_metrics,
            "warnings": latest.warnings,
            "result_channel": "BACKTEST",
        },
        "models": [
            {
                "model_id": m.model_id,
                "status": m.status,
                "test_metrics": m.test_metrics,
                "warnings": m.warnings,
            }
            for m in models
        ],
        "disclaimer": "Backtested and model metrics are not guarantees of future performance.",
    }


@router.get("/risk")
def risk():
    snap = _paper.snapshot({})
    s = get_settings()
    return {
        "paper": {
            "drawdown": snap["drawdown"],
            "equity": snap["equity"],
            "open_positions": len(snap["positions"]),
        },
        "limits": {
            "max_risk_per_trade": s.max_risk_per_trade,
            "max_position_size": s.max_position_size,
            "max_sector_exposure": s.max_sector_exposure,
            "max_portfolio_drawdown": s.max_portfolio_drawdown,
            "daily_loss_limit": s.daily_loss_limit,
        },
        "result_channel": "PAPER",
    }


@router.get("/portfolio", response_model=PortfolioOut)
def portfolio(db: Session = Depends(get_db)):
    marks = {}
    for sym in list(_paper.account.positions.keys()):
        df = prices_frame(db, sym)
        if not df.empty:
            marks[sym] = float(df.iloc[-1]["close"])
    return _paper.snapshot(marks)


@router.post("/portfolio/orders")
def place_paper_order(symbol: str, side: str, qty: int, db: Session = Depends(get_db)):
    df = prices_frame(db, symbol.upper())
    if df.empty:
        raise HTTPException(404, "No price for symbol")
    px = float(df.iloc[-1]["close"])
    result = _paper.place_order(PaperOrder(symbol=symbol.upper(), side=side.upper(), qty=qty), px)
    return result


@router.get("/backtests")
def list_backtests(db: Session = Depends(get_db)):
    rows = db.query(Backtest).order_by(Backtest.created_at.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "strategy": r.strategy,
            "metrics": r.metrics,
            "warnings": r.warnings,
            "result_channel": r.result_channel,
        }
        for r in rows
    ]


@router.get("/backtests/{backtest_id}", response_model=BacktestOut)
def get_backtest(backtest_id: int, db: Session = Depends(get_db)):
    row = db.query(Backtest).filter_by(id=backtest_id).first()
    if not row:
        raise HTTPException(404, "Backtest not found")
    return BacktestOut(
        id=row.id,
        name=row.name,
        strategy=row.strategy,
        metrics=row.metrics,
        benchmark_metrics=row.benchmark_metrics,
        warnings=row.warnings,
        equity_curve=row.equity_curve,
        drawdown_curve=row.drawdown_curve,
        monthly_returns=row.monthly_returns,
        result_channel=row.result_channel,
    )


@router.post("/backtests", response_model=BacktestOut)
def create_backtest(body: BacktestCreate, db: Session = Depends(get_db)):
    prices = {}
    for sym in set(body.symbols + ["NIFTY_50"]):
        df = prices_frame(db, sym)
        if not df.empty:
            prices[sym] = df
    if len(prices) < 2:
        raise HTTPException(400, "Insufficient price data. Run seed/ingest first.")

    def signal_fn(symbol: str, d: date, row):
        # simple momentum rule for deterministic example backtests
        # uses only current row fields already computed historically
        ret5 = None
        # approximate from close path available in prices up to d
        hist = prices[symbol]
        hist = hist[hist["trade_date"] <= d]
        if len(hist) < 6:
            return None
        c = hist["close"].astype(float)
        ret5 = float(c.iloc[-1] / c.iloc[-6] - 1)
        rsi_proxy = ret5
        if ret5 > 0.02:
            px = float(row["close"])
            return {"action": "BUY", "stop": px * 0.97, "target": px * 1.06, "sector": "UNKNOWN"}
        return {"action": "HOLD"}

    engine = EventDrivenBacktester(
        prices,
        initial_capital=body.initial_capital,
        risk_per_trade=body.risk_per_trade,
        max_position_pct=body.max_position_size,
    )
    result = engine.run(body.start_date, body.end_date, signal_fn, symbols=body.symbols)

    bt = Backtest(
        name=body.name,
        strategy=body.strategy,
        universe={"symbols": body.symbols},
        start_date=body.start_date,
        end_date=body.end_date,
        initial_capital=Decimal(str(body.initial_capital)),
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
    db.refresh(bt)

    for t in result.trades:
        stock = db.query(Stock).filter_by(symbol=t["symbol"]).first()
        if not stock:
            continue
        db.add(
            BacktestTrade(
                backtest_id=bt.id,
                stock_id=stock.id,
                entry_date=date.fromisoformat(t["entry_date"]),
                exit_date=date.fromisoformat(t["exit_date"]) if t.get("exit_date") else None,
                qty=t["qty"],
                entry_price=Decimal(str(t["entry_price"])),
                exit_price=Decimal(str(t["exit_price"])) if t.get("exit_price") is not None else None,
                stop_loss=Decimal(str(t["stop_loss"])) if t.get("stop_loss") is not None else None,
                take_profit=Decimal(str(t["take_profit"])) if t.get("take_profit") is not None else None,
                costs=Decimal(str(t.get("costs") or 0)),
                pnl=Decimal(str(t["pnl"])) if t.get("pnl") is not None else None,
                return_pct=Decimal(str(t["return_pct"])) if t.get("return_pct") is not None else None,
                exit_reason=t.get("exit_reason"),
            )
        )
    db.commit()

    return BacktestOut(
        id=bt.id,
        name=bt.name,
        strategy=bt.strategy,
        metrics=bt.metrics,
        benchmark_metrics=bt.benchmark_metrics,
        warnings=bt.warnings,
        equity_curve=bt.equity_curve,
        drawdown_curve=bt.drawdown_curve,
        monthly_returns=bt.monthly_returns,
        result_channel="BACKTEST",
    )


@router.get("/data-quality")
def data_quality(db: Session = Depends(get_db)):
    rows = db.query(DataQualityLog).order_by(DataQualityLog.checked_at.desc()).limit(200).all()
    return [
        {
            "id": r.id,
            "stock_id": r.stock_id,
            "check_type": r.check_type,
            "severity": r.severity,
            "message": r.message,
            "details": r.details,
            "checked_at": r.checked_at.isoformat() if r.checked_at else None,
        }
        for r in rows
    ]
