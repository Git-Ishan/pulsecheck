from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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
    last_checked_at: datetime | None
    last_response_time_ms: int | None
    last_http_status: int | None
    created_at: datetime
