from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checker import CheckOutcome
from app.config import FAILURE_THRESHOLD, STALE_STREAK_SECONDS
from app.models import CheckResult, Incident, Monitor
from app.state import next_state


def _as_utc(value: datetime | None) -> datetime | None:
    # SQLite returns datetimes without a timezone; ours are always UTC.
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def record_check(
    db: Session, monitor: Monitor, outcome: CheckOutcome, started_at: datetime
) -> CheckResult:
    previous = _as_utc(monitor.last_checked_at)
    stale = (
        previous is not None
        and (started_at - previous).total_seconds() > STALE_STREAK_SECONDS
    )

    result = CheckResult(
        monitor_id=monitor.id,
        checked_at=started_at,
        healthy=outcome.healthy,
        http_status_code=outcome.http_status_code,
        response_time_ms=outcome.response_time_ms,
        error_type=outcome.error_type,
    )
    db.add(result)

    monitor.last_checked_at = started_at
    monitor.last_response_time_ms = outcome.response_time_ms
    monitor.last_http_status = outcome.http_status_code

    transition = next_state(
        monitor.current_status,
        monitor.consecutive_failures,
        outcome.healthy,
        FAILURE_THRESHOLD,
        stale,
    )
    monitor.current_status = transition.status
    monitor.consecutive_failures = transition.consecutive_failures

    if transition.event == "went_down":
        db.add(Incident(monitor_id=monitor.id, started_at=started_at))
    elif transition.event == "recovered":
        open_incident = db.scalar(
            select(Incident).where(
                Incident.monitor_id == monitor.id, Incident.resolved_at.is_(None)
            )
        )
        if open_incident is not None:
            open_incident.resolved_at = started_at

    db.commit()
    db.refresh(result)
    return result
