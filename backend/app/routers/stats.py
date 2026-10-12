from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Monitor
from app.schemas import StatsRead

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsRead)
def get_stats(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Monitor.current_status, func.count()).group_by(Monitor.current_status)
    ).all()
    counts = {status: n for status, n in rows}
    return StatsRead(
        total=sum(counts.values()),
        up=counts.get("UP", 0),
        down=counts.get("DOWN", 0),
        unknown=counts.get("UNKNOWN", 0),
    )
