import asyncio

import httpx
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app import scheduler
from app.models import CheckResult, Monitor


def add_monitors(db, urls):
    for url in urls:
        db.add(Monitor(url=url))
    db.commit()


def run_cycle_with(handler):
    async def go():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            await scheduler.run_cycle(client)

    asyncio.run(go())


def test_concurrency_never_exceeds_limit(db, monkeypatch):
    monkeypatch.setattr(scheduler, "SessionLocal", sessionmaker(bind=db.get_bind()))
    monkeypatch.setattr(scheduler, "MAX_CONCURRENT_CHECKS", 3)
    add_monitors(db, [f"http://site{i}.test/" for i in range(10)])

    running = 0
    max_running = 0

    async def handler(request):
        nonlocal running, max_running
        running += 1
        max_running = max(max_running, running)
        await asyncio.sleep(0.05)
        running -= 1
        return httpx.Response(200)

    run_cycle_with(handler)

    assert max_running == 3
    assert len(db.scalars(select(CheckResult)).all()) == 10


def test_slow_monitor_does_not_block_others(db, monkeypatch):
    monkeypatch.setattr(scheduler, "SessionLocal", sessionmaker(bind=db.get_bind()))
    monkeypatch.setattr(scheduler, "MAX_CONCURRENT_CHECKS", 10)
    add_monitors(db, ["http://slow.test/", "http://fast1.test/", "http://fast2.test/"])

    finished = []

    async def handler(request):
        host = request.url.host
        if host == "slow.test":
            await asyncio.sleep(0.3)
        finished.append(host)
        return httpx.Response(200)

    run_cycle_with(handler)

    assert set(finished) == {"slow.test", "fast1.test", "fast2.test"}
    assert finished[-1] == "slow.test"
