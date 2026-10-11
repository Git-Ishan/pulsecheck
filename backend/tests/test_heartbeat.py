import asyncio
from datetime import timedelta

from app import heartbeat, scheduler
from app.main import app
from app.models import utcnow

NOW = utcnow()
LIMIT = 100


# --- the pure decision function ---

def test_dead_task_is_stopped():
    assert heartbeat.evaluate(NOW, NOW, NOW, False, LIMIT) == "stopped"


def test_never_started():
    assert heartbeat.evaluate(NOW, None, None, True, LIMIT) == "not_started"


def test_started_but_no_cycle_yet_is_starting():
    started = NOW - timedelta(seconds=5)
    assert heartbeat.evaluate(NOW, started, None, True, LIMIT) == "starting"


def test_no_cycle_for_too_long_is_stalled():
    started = NOW - timedelta(seconds=500)
    assert heartbeat.evaluate(NOW, started, None, True, LIMIT) == "stalled"


def test_recent_cycle_is_ok():
    started = NOW - timedelta(seconds=1000)
    finished = NOW - timedelta(seconds=10)
    assert heartbeat.evaluate(NOW, started, finished, True, LIMIT) == "ok"


def test_old_cycle_is_stalled():
    started = NOW - timedelta(seconds=1000)
    finished = NOW - timedelta(seconds=500)
    assert heartbeat.evaluate(NOW, started, finished, True, LIMIT) == "stalled"


# --- the endpoint ---

class FakeTask:
    def __init__(self, alive):
        self.alive = alive

    def done(self):
        return not self.alive


def set_task(monkeypatch, alive):
    monkeypatch.setattr(app.state, "scheduler_task", FakeTask(alive), raising=False)


def test_endpoint_reports_ok(client, monkeypatch):
    set_task(monkeypatch, True)
    heartbeat.mark_started(utcnow())
    heartbeat.mark_cycle_finished(utcnow())
    response = client.get("/health/scheduler")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["cycles_completed"] == 1


def test_endpoint_returns_503_when_task_is_dead(client, monkeypatch):
    set_task(monkeypatch, False)
    heartbeat.mark_started(utcnow())
    response = client.get("/health/scheduler")
    assert response.status_code == 503
    assert response.json()["status"] == "stopped"


def test_endpoint_returns_503_when_stalled(client, monkeypatch):
    set_task(monkeypatch, True)
    long_ago = utcnow() - timedelta(hours=1)
    heartbeat.mark_started(long_ago)
    heartbeat.mark_cycle_finished(long_ago)
    response = client.get("/health/scheduler")
    assert response.status_code == 503
    assert response.json()["status"] == "stalled"


def test_endpoint_without_a_scheduler_is_503(client):
    response = client.get("/health/scheduler")
    assert response.status_code == 503


# --- the loop itself ---

def test_loop_survives_a_crashing_cycle(monkeypatch):
    calls = {"n": 0}

    async def flaky_cycle(client):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")

    monkeypatch.setattr(scheduler, "run_cycle", flaky_cycle)
    monkeypatch.setattr(scheduler, "CHECK_INTERVAL_SECONDS", 0.01)

    async def go():
        task = asyncio.create_task(scheduler.scheduler_loop())
        await asyncio.sleep(0.2)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(go())
    assert calls["n"] >= 2  # it kept going after the crash
    assert heartbeat.state.cycles_completed >= 1
