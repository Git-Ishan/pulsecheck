import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checker import CHECK_TIMEOUT, check_url
from app.database import get_db
from app.models import CheckResult, Incident, Monitor, utcnow
from app.monitoring import record_check
from app.schemas import CheckResultRead, IncidentRead, MonitorCreate, MonitorRead
from app.urlsafety import UnsafeURLError, check_url_allowed

router = APIRouter(prefix="/monitors", tags=["monitors"])


def get_monitor_or_404(monitor_id: int, db: Session) -> Monitor:
    monitor = db.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor


@router.post("", response_model=MonitorRead, status_code=201)
def create_monitor(payload: MonitorCreate, db: Session = Depends(get_db)):
    try:
        check_url_allowed(str(payload.url))
    except UnsafeURLError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    monitor = Monitor(name=payload.name, url=str(payload.url))
    db.add(monitor)
    db.commit()
    db.refresh(monitor)
    return monitor


@router.get("", response_model=list[MonitorRead])
def list_monitors(db: Session = Depends(get_db)):
    return db.scalars(select(Monitor).order_by(Monitor.id)).all()


@router.get("/{monitor_id}", response_model=MonitorRead)
def get_monitor(monitor_id: int, db: Session = Depends(get_db)):
    return get_monitor_or_404(monitor_id, db)


@router.delete("/{monitor_id}", status_code=204)
def delete_monitor(monitor_id: int, db: Session = Depends(get_db)):
    monitor = get_monitor_or_404(monitor_id, db)
    db.delete(monitor)
    db.commit()
@router.post("/{monitor_id}/check", response_model=CheckResultRead)
async def run_manual_check(monitor_id: int, db: Session = Depends(get_db)):
    monitor = get_monitor_or_404(monitor_id, db)
    started_at = utcnow()
    async with httpx.AsyncClient(timeout=CHECK_TIMEOUT, follow_redirects=False) as client:
        outcome = await check_url(monitor.url, client)
    return record_check(db, monitor, outcome, started_at)

@router.get("/{monitor_id}/checks", response_model=list[CheckResultRead])
def list_checks(
    monitor_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    get_monitor_or_404(monitor_id, db)
    stmt = (
        select(CheckResult)
        .where(CheckResult.monitor_id == monitor_id)
        .order_by(CheckResult.checked_at.desc(), CheckResult.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return db.scalars(stmt).all()


@router.get("/{monitor_id}/incidents", response_model=list[IncidentRead])
def list_incidents(
    monitor_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    get_monitor_or_404(monitor_id, db)
    stmt = (
        select(Incident)
        .where(Incident.monitor_id == monitor_id)
        .order_by(Incident.started_at.desc(), Incident.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return db.scalars(stmt).all()
