from datetime import timedelta

from app.models import CheckResult, Monitor, utcnow


def make_monitor(db, status="UNKNOWN"):
    monitor = Monitor(url="http://test.local", current_status=status)
    db.add(monitor)
    db.commit()
    return monitor


def add_check(db, monitor, healthy, hours_ago=1.0, error_type=None, ms=None):
    db.add(
        CheckResult(
            monitor_id=monitor.id,
            checked_at=utcnow() - timedelta(hours=hours_ago),
            healthy=healthy,
            http_status_code=200 if healthy else None,
            response_time_ms=ms,
            error_type=error_type,
        )
    )
    db.commit()


# --- /stats ---

def test_stats_counts_monitors_by_status(anon_client, db):
    for status in ["UP", "UP", "DOWN", "UNKNOWN"]:
        make_monitor(db, status)
    response = anon_client.get("/stats")  # public: no key needed
    assert response.status_code == 200
    assert response.json() == {"total": 4, "up": 2, "down": 1, "unknown": 1}


def test_stats_with_no_monitors(anon_client):
    assert anon_client.get("/stats").json() == {"total": 0, "up": 0, "down": 0, "unknown": 0}


# --- uptime ---

def test_uptime_percentage(anon_client, db):
    monitor = make_monitor(db)
    for _ in range(3):
        add_check(db, monitor, True, ms=100)
    add_check(db, monitor, False, error_type="timeout")
    body = anon_client.get(f"/monitors/{monitor.id}/uptime").json()
    assert body["uptime_percent"] == 75.0
    assert body["sample_size"] == 4
    assert body["successful_checks"] == 3
    assert body["failed_checks"] == 1


def test_uptime_ignores_checks_outside_the_window(anon_client, db):
    monitor = make_monitor(db)
    add_check(db, monitor, False, hours_ago=48, error_type="timeout")
    add_check(db, monitor, True, hours_ago=1, ms=50)
    body = anon_client.get(f"/monitors/{monitor.id}/uptime?hours=24").json()
    assert body["sample_size"] == 1
    assert body["uptime_percent"] == 100.0


def test_uptime_counts_blocked_and_dns_failures_as_failures(anon_client, db):
    monitor = make_monitor(db)
    add_check(db, monitor, True, ms=10)
    add_check(db, monitor, False, error_type="blocked_destination")
    add_check(db, monitor, False, error_type="dns_error")
    body = anon_client.get(f"/monitors/{monitor.id}/uptime").json()
    assert body["uptime_percent"] == 33.33
    assert body["failed_checks"] == 2


def test_uptime_with_no_checks_is_null(anon_client, db):
    monitor = make_monitor(db)
    body = anon_client.get(f"/monitors/{monitor.id}/uptime").json()
    assert body["sample_size"] == 0
    assert body["uptime_percent"] is None
    assert body["average_response_time_ms"] is None


def test_average_response_time_uses_successful_checks_only(anon_client, db):
    monitor = make_monitor(db)
    add_check(db, monitor, True, ms=100)
    add_check(db, monitor, True, ms=300)
    add_check(db, monitor, False, error_type="timeout")
    body = anon_client.get(f"/monitors/{monitor.id}/uptime").json()
    assert body["average_response_time_ms"] == 200


def test_uptime_only_counts_the_requested_monitor(anon_client, db):
    mine = make_monitor(db)
    other = make_monitor(db)
    add_check(db, mine, True, ms=10)
    add_check(db, other, False, error_type="timeout")
    body = anon_client.get(f"/monitors/{mine.id}/uptime").json()
    assert body["sample_size"] == 1
    assert body["uptime_percent"] == 100.0


def test_uptime_for_unknown_monitor_is_404(anon_client):
    assert anon_client.get("/monitors/999/uptime").status_code == 404


def test_uptime_window_is_validated(anon_client, db):
    monitor = make_monitor(db)
    assert anon_client.get(f"/monitors/{monitor.id}/uptime?hours=0").status_code == 422
    assert anon_client.get(f"/monitors/{monitor.id}/uptime?hours=1000").status_code == 422
