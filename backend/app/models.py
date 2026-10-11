from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Monitor(Base):
    __tablename__ = "monitors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(2048))
    enabled: Mapped[bool] = mapped_column(default=True)

    current_status: Mapped[str] = mapped_column(String(10), default="UNKNOWN")
    consecutive_failures: Mapped[int] = mapped_column(default=0)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_response_time_ms: Mapped[int | None]
    last_http_status: Mapped[int | None]

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    checks: Mapped[list["CheckResult"]] = relationship(
        back_populates="monitor", cascade="all, delete-orphan"
    )
    incidents: Mapped[list["Incident"]] = relationship(
        cascade="all, delete-orphan"
    )


class CheckResult(Base):
    __tablename__ = "check_results"
    __table_args__ = (Index("ix_check_monitor_time", "monitor_id", "checked_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("monitors.id"))
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    healthy: Mapped[bool]
    http_status_code: Mapped[int | None]
    response_time_ms: Mapped[int | None]
    error_type: Mapped[str | None] = mapped_column(String(50))

    monitor: Mapped["Monitor"] = relationship(back_populates="checks")


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index(
            "uq_one_open_incident_per_monitor",
            "monitor_id",
            unique=True,
            sqlite_where=text("resolved_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("monitors.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
