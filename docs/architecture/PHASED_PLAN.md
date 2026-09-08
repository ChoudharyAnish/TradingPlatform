# Phased Implementation Plan

| Phase | Goal | Exit criteria |
|-------|------|---------------|
| 1 Foundation | Repo, Docker, FastAPI, Next.js, Postgres, Alembic, logging, tests | `make up` + health API + frontend load + migrations apply |
| 2 Market Data | Provider interfaces, ingest, storage, DQ checks | Ingest sample universe; DQ report API |
| 3 Features | Technical + market context features, storage | Feature compute job; no look-ahead unit tests |
| 4 ML | Baselines, XGB/LGBM, calibration, registry | Train script writes model_run + metrics |
| 5 Backtesting | Event engine, costs, walk-forward, metrics | Example backtest vs NIFTY buy&hold |
| 6 Signals | Ensemble, risk sizing, screener APIs | Signal payload with full risk fields |
| 7 Dashboard | Home, predictions, stock detail, backtest, models | UI wired to APIs |
| 8 Paper Trading | Virtual portfolio, fills, P&L, alerts | Paper session distinct from backtest |

## Risks remaining after v1

- Live market data ToS / paid feed dependency  
- Fundamentals/news coverage gaps → sentiment/fundamental heads may be weak or disabled  
- Yahoo Finance not exchange-authoritative  
- Parameter optimization still can overfit if misused — warnings help but do not eliminate risk  
