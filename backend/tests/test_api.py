from datetime import timedelta

from sqlalchemy import select

from app.database import get_db
from app.main import app
from app.models import CheckResult, Monitor, utcnow


def add_monitor(db, url="http://test.local"):
    monitor = Monitor(url=url)
    db.add(monitor)
    db.commit()
    return monitor


# --- health and readiness ---

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_when_database_works(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_returns_503_when_database_fails(client):
    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise RuntimeError("db is down")

    def broken_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    response = client.get("/ready")
    assert response.status_code == 503


# --- creating monitors ---

def test_create_monitor(client):
    response = client.post("/monitors", json={"name": "Example", "url": "https://example.com"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Example"
    assert body["url"] == "https://example.com/"
    assert body["current_status"] == "UNKNOWN"
    assert body["consecutive_failures"] == 0
    assert body["enabled"] is True


def test_create_rejects_malformed_url(client):
    response = client.post("/monitors", json={"url": "hello"})
    assert response.status_code == 422


def test_create_rejects_non_http_scheme(client):
    response = client.post("/monitors", json={"url": "ftp://example.com"})
    assert response.status_code == 422


def test_create_rejects_missing_url(client):
    response = client.post("/monitors", json={"name": "No URL"})
    assert response.status_code == 422


# --- listing, reading, deleting ---

def test_list_monitors(client):
    client.post("/monitors", json={"url": "https://a.example.com"})
    client.post("/monitors", json={"url": "https://b.example.com"})
    response = client.get("/monitors")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_get_unknown_monitor_returns_404(client):
    response = client.get("/monitors/999")
    assert response.status_code == 404


def test_delete_monitor(client):
    created = client.post("/monitors", json={"url": "https://example.com"}).json()
    assert client.delete(f"/monitors/{created['id']}").status_code == 204
    assert client.get(f"/monitors/{created['id']}").status_code == 404


def test_delete_removes_check_history(client, db):
    monitor = add_monitor(db)
    monitor_id = monitor.id
    db.add(CheckResult(monitor_id=monitor_id, healthy=True))
    db.commit()

    assert client.delete(f"/monitors/{monitor_id}").status_code == 204
    assert db.scalars(select(CheckResult)).all() == []


# --- persistence ---

def test_created_monitor_is_stored_in_database(client, db):
    created = client.post("/monitors", json={"url": "https://example.com"}).json()
    stored = db.get(Monitor, created["id"])
    assert stored is not None
    assert stored.url == "https://example.com/"


# --- check history ---

def test_checks_are_newest_first(client, db):
    monitor = add_monitor(db)
    start = utcnow()
    for i in range(3):
        db.add(
            CheckResult(
                monitor_id=monitor.id,
                checked_at=start + timedelta(seconds=i),
                healthy=True,
                response_time_ms=i,
            )
        )
    db.commit()

    response = client.get(f"/monitors/{monitor.id}/checks")
    assert response.status_code == 200
    assert [c["response_time_ms"] for c in response.json()] == [2, 1, 0]


def test_checks_limit_is_capped(client, db):
    monitor = add_monitor(db)
    response = client.get(f"/monitors/{monitor.id}/checks?limit=1000")
    assert response.status_code == 422


def test_checks_for_unknown_monitor_returns_404(client):
    assert client.get("/monitors/999/checks").status_code == 404
