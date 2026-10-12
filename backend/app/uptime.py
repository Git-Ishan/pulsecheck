from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import CheckResult


def compute_uptime(db: Session, monitor_id: int, since: datetime) -> dict:
    stmt = select(
        func.count(),
        func.sum(case((CheckResult.healthy, 1), else_=0)),
        func.avg(case((CheckResult.healthy, CheckResult.response_time_ms))),
    ).where(
        CheckResult.monitor_id == monitor_id,
        CheckResult.checked_at >= since,
    )
    total, ok, avg = db.execute(stmt).one()
    ok = int(ok or 0)
    return {
        "sample_size": total,
        "successful_checks": ok,
        "failed_checks": total - ok,
        "uptime_percent": round(ok / total * 100, 2) if total else None,
        "average_response_time_ms": round(avg) if avg is not None else None,
    }
