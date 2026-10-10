from datetime import datetime

from sqlalchemy.orm import Session

from app.checker import CheckOutcome
from app.models import CheckResult, Monitor


def record_check(
    db: Session, monitor: Monitor, outcome: CheckOutcome, started_at: datetime
) -> CheckResult:
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

    db.commit()
    db.refresh(result)
    return result
