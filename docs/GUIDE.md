# Operator Guide

## Install

```bash
cp .env.example .env
# Docker (recommended)
make up
make migrate
make seed

# Or local
cd backend && pip install -e ".[dev]"
cd ../frontend && npm install
```

## Configure

Edit `.env` and `config/*.yaml`:

- `MARKET_DATA_PROVIDER=csv_sample|yahoo`
- Risk: `MAX_RISK_PER_TRADE`, `MAX_POSITION_SIZE`, …
- Costs: `config/transaction_costs.yaml` (see `docs/research/transaction-costs.md`)
- Universe: `config/universe.yaml`

Never commit secrets. API keys stay server-side only.

## Ingest data

```bash
# sample (offline)
make seed

# optional Yahoo (research only)
# set YAHOO_ENABLED=true and MARKET_DATA_PROVIDER=yahoo
```

Add a provider by implementing interfaces in `backend/app/data/providers/base.py` and registering it in `get_historical_provider()`.

## Train models

```bash
docker compose exec api python -m scripts.train_models
```

Models are versioned in the registry (`model_runs` + `artifacts/models`). Experiments are append-only.

## Run backtests

```bash
docker compose exec api python -m scripts.run_example_backtest
# or POST /api/backtests
```

Results are labeled `result_channel=BACKTEST`.

## Paper trading

```bash
docker compose exec api python -m scripts.start_paper_trading
# dashboard: /portfolio
```

No live order routing. Future brokers should implement the `PaperBroker`-like interface (`LiveBrokerAdapter` stub).

## Interpret predictions

Every signal includes probability, expected return/downside, stop/target, position size, regime, model version, and feature contributions. Confidence is derived from calibrated probability margin — not invented.

Poor models are reported with warnings (`OVERFITTING_RISK`, `POOR_OUT_OF_SAMPLE_PERFORMANCE`, …). Do not “fix” metrics.

## Add a model

1. Add builder in `app/ml/train.py` `_build_estimator`
2. Include in `scripts/train_models.py`
3. Register via `register_model`
4. Promote status only after honest OOS review

## Add a broker later

Implement against `app/portfolio/paper.py` interface. Keep paper and live ledgers separate. Require explicit config flag before any live path.

## Bias controls

See `docs/architecture/ANTI_OVERFITTING.md`.
