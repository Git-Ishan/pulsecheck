import asyncio
import logging
import time

import httpx
from sqlalchemy import select

from app.checker import CHECK_TIMEOUT, check_url
from app.config import CHECK_INTERVAL_SECONDS, MAX_CONCURRENT_CHECKS
from app.database import SessionLocal
from app.models import Monitor, utcnow
from app.monitoring import record_check

logger = logging.getLogger("pulsecheck.scheduler")


async def check_and_record(
    monitor_id: int, url: str, client: httpx.AsyncClient, semaphore: asyncio.Semaphore
) -> None:
    try:
        async with semaphore:
            started_at = utcnow()
            outcome = await check_url(url, client)

        with SessionLocal() as db:
            monitor = db.get(Monitor, monitor_id)
            if monitor is None:
                return  # deleted while the check was running
            record_check(db, monitor, outcome, started_at)

        logger.info(
            "Checked monitor %s: healthy=%s status=%s",
            monitor_id, outcome.healthy, outcome.http_status_code,
        )
    except Exception:
        logger.exception("Check failed for monitor %s", monitor_id)


async def run_cycle(client: httpx.AsyncClient) -> None:
    cycle_start = time.perf_counter()

    with SessionLocal() as db:
        monitors = db.scalars(select(Monitor).where(Monitor.enabled)).all()
        targets = [(m.id, m.url) for m in monitors]

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHECKS)
    await asyncio.gather(
        *(check_and_record(mid, url, client, semaphore) for mid, url in targets)
    )

    logger.info(
        "Cycle finished: %d monitors in %.1fs",
        len(targets), time.perf_counter() - cycle_start,
    )


async def scheduler_loop() -> None:
    async with httpx.AsyncClient(timeout=CHECK_TIMEOUT, follow_redirects=False) as client:
        while True:
            try:
                await run_cycle(client)
            except Exception:
                logger.exception("Monitoring cycle crashed")
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
