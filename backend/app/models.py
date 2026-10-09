from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

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
