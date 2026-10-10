import asyncio
import logging

import httpx
from sqlalchemy import select

from app.checker import CHECK_TIMEOUT, check_url
from app.config import CHECK_INTERVAL_SECONDS
from app.database import SessionLocal
from app.models import Monitor, utcnow
from app.monitoring import record_check

logger = logging.getLogger("pulsecheck.scheduler")


async def run_cycle(client: httpx.AsyncClient) -> None:
    with SessionLocal() as db:
        monitors = db.scalars(select(Monitor).where(Monitor.enabled)).all()
        for monitor in monitors:
            monitor_id = monitor.id
            try:
                started_at = utcnow()
                outcome = await check_url(monitor.url, client)
                record_check(db, monitor, outcome, started_at)
                logger.info(
                    "Checked monitor %s: healthy=%s status=%s",
                    monitor_id, outcome.healthy, outcome.http_status_code,
                )
            except Exception:
                logger.exception("Check failed for monitor %s", monitor_id)
                db.rollback()


async def scheduler_loop() -> None:
    async with httpx.AsyncClient(timeout=CHECK_TIMEOUT, follow_redirects=False) as client:
        while True:
            try:
                await run_cycle(client)
            except Exception:
                logger.exception("Monitoring cycle crashed")
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
