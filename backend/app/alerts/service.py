"""Pluggable alert notification providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Alert


@dataclass
class AlertEvent:
    alert_type: str
    message: str
    severity: str = "INFO"
    payload: Optional[dict] = None


class NotificationProvider(ABC):
    @abstractmethod
    def send(self, event: AlertEvent) -> bool:
        raise NotImplementedError


class LogNotificationProvider(NotificationProvider):
    def send(self, event: AlertEvent) -> bool:
        from app.core.logging import get_logger

        get_logger(__name__).info(
            "alert",
            alert_type=event.alert_type,
            severity=event.severity,
            message=event.message,
        )
        return True


class AlertService:
    def __init__(self, providers: Optional[list[NotificationProvider]] = None):
        self.providers = providers or [LogNotificationProvider()]

    def emit(self, db: Session, event: AlertEvent) -> Alert:
        row = Alert(
            alert_type=event.alert_type,
            severity=event.severity,
            message=event.message,
            payload=event.payload or {},
            delivered=False,
        )
        ok = all(p.send(event) for p in self.providers)
        row.delivered = ok
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
