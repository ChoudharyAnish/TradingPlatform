# Architecture — Indian Stock AI Platform

**Date:** 2026-09-08  
**Status:** Living document  
**Scope:** Indian equities research, prediction, backtesting, paper trading (no live order execution)

## 1. Purpose

A production-oriented quantitative research and paper-trading platform for NSE/BSE equities. The system maximizes statistically defensible risk-adjusted expectancy while controlling drawdowns and overfitting. It does **not** guarantee profits, eliminate losses, or claim perfect prediction accuracy.

Predictions always include probability/confidence, expected return/downside, risk/reward, position size, stop/target, horizon, model version, and feature-based explanations.

Results are strictly labeled as:

1. **Backtested** — historical simulation only  
2. **Paper trading** — simulated live execution  
3. **Live market** — reserved for future broker adapters (not implemented)

## 2. High-level architecture

```text
┌─────────────┐   ┌──────────────┐   ┌────────────────┐
│  Data        │→  │  Features    │→  │  ML / Ensemble │
│  Providers   │   │  Pipeline    │   │  + Calibration │
└─────────────┘   └──────────────┘   └───────┬────────┘
                                             ↓
┌─────────────┐   ┌──────────────┐   ┌────────────────┐
│  Dashboard   │←  │  API Layer   │←  │  Signals/Risk  │
│  (Next.js)   │   │  (FastAPI)   │   │  + Paper Trade │
└─────────────┘   └──────────────┘   └───────┬────────┘
                                             ↓
                              ┌──────────────────────────┐
                              │ PostgreSQL + Redis       │
                              │ Model Registry / Artifacts│
                              └──────────────────────────┘
```

### Layers

| Layer | Responsibility |
|-------|----------------|
| Data | Pluggable providers → normalized OHLCV, corporate actions, fundamentals, news |
| Features | Timestamp-aware technical/fundamental/sentiment/regime features; no leakage |
| ML | Baselines + XGBoost/LightGBM; walk-forward; calibration; registry |
| Ensemble | Weighted blend of technical/fundamental/regime/sentiment heads |
| Backtest | Event-driven engine with Indian transaction costs, slippage, stops |
| Risk | Position sizing, sector/correlation limits, drawdown circuit breakers |
| Signals | STRONG_BUY…STRONG_SELL with full risk metadata |
| Portfolio | Paper trading virtual capital & P&L |
| API | REST + OpenAPI; auth-ready |
| Frontend | Research dashboard, screener, backtests, models |

## 3. Tech stack

- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, Celery/APScheduler  
- **DB/Cache:** PostgreSQL 16, Redis 7  
- **ML:** pandas, NumPy, scikit-learn, XGBoost, LightGBM, SHAP  
- **Frontend:** Next.js 14 (App Router), TypeScript, Tailwind CSS, Lightweight Charts  
- **Infra:** Docker Compose, Makefile, GitHub Actions  

## 4. Data provider strategy

Providers implement abstract interfaces (`MarketDataProvider`, `HistoricalDataProvider`, etc.). Default runtime uses:

1. **CSVSampleProvider** — reproducible offline sample (CI/demo)  
2. **YahooFinanceProvider** — optional live historical pull for NSE symbols (`SYMBOL.NS`)  

Official NSE paid EOD/SFTP and broker APIs (Zerodha, etc.) are adapter stubs for later. Scraping NSE web endpoints is **not** the primary production path due to ToS/reliability risks.

See `docs/research/data-providers.md`.

## 5. Database

PostgreSQL schemas cover instruments, prices, corporate actions, features, model runs/predictions, signals, backtests, portfolio, risk metrics, and data-quality logs. Migrations via Alembic.

## 6. Anti-overfitting controls

- Chronological / walk-forward splits only (no random shuffle of time series)  
- Explicit feature lag; adjusted prices for returns; point-in-time universe filters  
- Overfitting risk flags: low sample size, unstable OOS metrics, regime fragility, extreme train–test gap  
- Only `VALIDATED` / `PAPER_TRADING` registry models emit production signals  

## 7. Security

- Secrets via env / `.env` (never committed)  
- Pydantic validation on all API inputs  
- Rate limiting middleware  
- Auth-ready JWT hooks (disabled by default for local research)  
- No credentials in frontend  

## 8. Phased delivery

See `docs/architecture/PHASED_PLAN.md`.

## 9. Explicit non-goals (v1)

- Live broker order placement  
- Options/F&O strategy engine  
- Guaranteed alpha or marketing performance claims  
