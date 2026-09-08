"""Simple filesystem + DB model registry helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.ml.train import TrainedModel, load_model, save_model
from app.models import ModelRun


ALLOWED_SIGNAL_STATUSES = {"VALIDATED", "PAPER_TRADING"}


def register_model(
    db: Session,
    model: TrainedModel,
    *,
    version: str,
    dataset_version: str,
    splits: dict,
    status: str = "EXPERIMENTAL",
) -> ModelRun:
    settings = get_settings()
    model_id = f"{model.model_type}-{version}"
    artifact_dir = settings.resolve_path(settings.model_artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    path = artifact_dir / f"{model_id}.joblib"
    save_model(model, path)

    run = ModelRun(
        model_id=model_id,
        model_type=model.model_type,
        version=version,
        training_date=datetime.now(timezone.utc),
        features=model.feature_names,
        parameters={"calibrated": model.calibrated},
        validation_metrics=model.valid_metrics,
        test_metrics=model.test_metrics,
        artifact_location=str(path),
        status=status,
        warnings=model.warnings,
        dataset_version=dataset_version,
        train_start=splits.get("train_start"),
        train_end=splits.get("train_end"),
        valid_start=splits.get("valid_start"),
        valid_end=splits.get("valid_end"),
        test_start=splits.get("test_start"),
        test_end=splits.get("test_end"),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_production_model(db: Session) -> Optional[tuple[ModelRun, TrainedModel]]:
    run = (
        db.query(ModelRun)
        .filter(ModelRun.status.in_(list(ALLOWED_SIGNAL_STATUSES)))
        .order_by(ModelRun.training_date.desc())
        .first()
    )
    if not run:
        # fall back to latest experimental for research UI
        run = db.query(ModelRun).order_by(ModelRun.training_date.desc()).first()
    if not run:
        return None
    model = load_model(Path(run.artifact_location))
    return run, model
