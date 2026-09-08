# Indian Stock AI — Prediction & Trading Research Platform

Serious quantitative research and **paper-trading** platform for Indian equities (NSE/BSE).

> **Not investment advice.** Predictions are probabilistic. Backtested results are **not** future guarantees. The system does not claim 100% accuracy, risk-free profits, or eliminated losses.

## What you get

- Configurable NSE/BSE universe (NIFTY 50 / Bank / Next 50 oriented)
- Pluggable market-data providers + sample dataset
- Feature engineering (technical + market context)
- Multiple ML models (sklearn baselines, XGBoost, LightGBM) with calibration & registry
- Event-driven backtester with Indian transaction-cost assumptions
- Walk-forward validation & overfitting risk flags
- Signal engine with risk sizing / stops / targets
- Stock screener + Next.js research dashboard
- Paper trading (no live broker execution in v1)
- Docker Compose, Alembic, tests, GitHub Actions CI

## Quick start

```bash
cp .env.example .env
make up          # postgres, redis, api, worker, frontend
make migrate
make seed        # sample prices + demo features/models
make test
```

- API docs: http://localhost:8000/docs  
- Dashboard: http://localhost:3000  

See [docs/GUIDE.md](docs/GUIDE.md) for ingest, train, backtest, paper trading, and extension guides.

## Architecture

See [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) and research notes under [docs/research/](docs/research/).

## Disclaimer

Past simulated performance ≠ future results. Always distinguish **backtest**, **paper**, and **live** results.
