"""Periodic jobs: DQ refresh and regime update (no live trading)."""

from __future__ import annotations

import time

from apscheduler.schedulers.blocking import BlockingScheduler

from app.core.logging import get_logger, setup_logging
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.market import load_universe, update_market_regime, compute_and_store_features

setup_logging(get_settings().debug)
logger = get_logger(__name__)


def job_regime():
    db = SessionLocal()
    try:
        snap = update_market_regime(db)
        logger.info("regime_job", regime=None if not snap else snap.regime)
    finally:
        db.close()


def job_features():
    db = SessionLocal()
    try:
        uni = load_universe()
        for sym in uni.get("universe", {}).get("symbols", []):
            n = compute_and_store_features(db, sym)
            logger.info("features_job", symbol=sym, rows=n)
    finally:
        db.close()


def main():
    sched = BlockingScheduler()
    sched.add_job(job_regime, "interval", hours=6, id="regime")
    sched.add_job(job_features, "interval", hours=12, id="features")
    logger.info("scheduler_started")
    # run once at boot
    job_regime()
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
