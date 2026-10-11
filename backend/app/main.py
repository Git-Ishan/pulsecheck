import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  (registers the tables)
from app.database import Base, engine
from app.routers import monitors
from app.scheduler import scheduler_loop

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(scheduler_loop())
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
