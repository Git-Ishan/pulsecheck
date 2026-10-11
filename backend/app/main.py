import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import heartbeat
from app import models  # noqa: F401  (registers the tables)
from app.config import SCHEDULER_STALE_SECONDS
from app.database import Base, engine, get_db
from app.models import utcnow
from app.routers import monitors
from app.scheduler import scheduler_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(scheduler_loop())
    app.state.scheduler_task = task
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="PulseCheck", lifespan=lifespan)
app.include_router(monitors.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
    return {"status": "ready"}


@app.get("/health/scheduler")
def scheduler_health(request: Request):
    task = getattr(request.app.state, "scheduler_task", None)
    state = heartbeat.state
    status = heartbeat.evaluate(
        now=utcnow(),
        started_at=state.started_at,
        last_cycle_finished_at=state.last_cycle_finished_at,
        task_alive=task is not None and not task.done(),
        max_age_seconds=SCHEDULER_STALE_SECONDS,
    )
    finished = state.last_cycle_finished_at
    body = {
        "status": status,
        "last_cycle_finished_at": finished.isoformat() if finished else None,
        "cycles_completed": state.cycles_completed,
    }
    code = 200 if status in heartbeat.HEALTHY else 503
    return JSONResponse(body, status_code=code)
