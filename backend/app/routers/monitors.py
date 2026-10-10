import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.checker import CHECK_TIMEOUT, check_url
from app.database import get_db
from app.models import Monitor, utcnow
from app.monitoring import record_check
from app.schemas import CheckResultRead, MonitorCreate, MonitorRead

router = APIRouter(prefix="/monitors", tags=["monitors"])


def get_monitor_or_404(monitor_id: int, db: Session) -> Monitor:
    monitor = db.get(Monitor, monitor_id)
    if monitor is None:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return monitor


@router.post("", response_model=MonitorRead, status_code=201)
def create_monitor(payload: MonitorCreate, db: Session = Depends(get_db)):
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