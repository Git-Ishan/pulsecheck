from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, HttpUrl


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


UtcDatetime = Annotated[datetime, AfterValidator(ensure_utc)]


class MonitorCreate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    url: HttpUrl


class MonitorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
    url: str
    enabled: bool
    current_status: str
    consecutive_failures: int
    last_checked_at: UtcDatetime | None
    last_response_time_ms: int | None
    last_http_status: int | None
    created_at: UtcDatetime


class CheckResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    monitor_id: int
    checked_at: UtcDatetime
    healthy: bool
    http_status_code: int | None
    response_time_ms: int | None
    error_type: str | None


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    monitor_id: int
    started_at: UtcDatetime
    resolved_at: UtcDatetime | None


class StatsRead(BaseModel):
    total: int
    up: int
    down: int
    unknown: int


class UptimeRead(BaseModel):
    monitor_id: int
    window_hours: int
    sample_size: int
    successful_checks: int
    failed_checks: int
    uptime_percent: float | None
    average_response_time_ms: int | None
