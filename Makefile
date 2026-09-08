.PHONY: up down build migrate seed test lint api frontend research-train backtest paper

up:
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build

migrate:
	docker compose exec api alembic upgrade head

seed:
	docker compose exec api python -m scripts.seed_sample_data

test:
	docker compose exec api pytest -q

lint:
	docker compose exec api ruff check app tests
	cd frontend && npm run lint

api:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

research-train:
	cd backend && python -m scripts.train_models

backtest:
	cd backend && python -m scripts.run_example_backtest

paper:
	cd backend && python -m scripts.start_paper_trading

install-backend:
	cd backend && pip install -e ".[dev]"

install-frontend:
	cd frontend && npm install
