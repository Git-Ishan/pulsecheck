from sqlalchemy import select

from app.checker import CheckOutcome
from app.models import CheckResult, Incident, Monitor, utcnow
from app.monitoring import record_check

OK = CheckOutcome(True, 200, 50, None)
FAIL = CheckOutcome(False, None, None, "timeout")


def make_monitor(db):
    monitor = Monitor(url="http://test.local")
    db.add(monitor)
    db.commit()
    return monitor


def feed(db, monitor, outcomes):
    for outcome in outcomes:
        record_check(db, monitor, outcome, utcnow())


def incidents(db):
    return db.scalars(select(Incident)).all()


def test_first_success_makes_monitor_up(db):
    monitor = make_monitor(db)
    feed(db, monitor, [OK])
    assert monitor.current_status == "UP"
    assert incidents(db) == []


def test_one_failure_does_not_open_incident(db):
    monitor = make_monitor(db)
    feed(db, monitor, [OK, FAIL])
    assert monitor.current_status == "UP"
    assert monitor.consecutive_failures == 1
    assert incidents(db) == []


def test_three_failures_open_one_incident(db):
    monitor = make_monitor(db)
    feed(db, monitor, [OK, FAIL, FAIL, FAIL])
    assert monitor.current_status == "DOWN"
    found = incidents(db)
    assert len(found) == 1
    assert found[0].resolved_at is None


def test_continuous_outage_does_not_duplicate_incident(db):
    monitor = make_monitor(db)
    feed(db, monitor, [OK] + [FAIL] * 8)
    assert len(incidents(db)) == 1


def test_recovery_resolves_incident(db):
    monitor = make_monitor(db)
    feed(db, monitor, [OK, FAIL, FAIL, FAIL, OK])
    assert monitor.current_status == "UP"
    assert monitor.consecutive_failures == 0
    found = incidents(db)
    assert len(found) == 1
    assert found[0].resolved_at is not None


def test_second_outage_creates_second_incident(db):
    monitor = make_monitor(db)
    feed(db, monitor, [OK] + [FAIL] * 3 + [OK] + [FAIL] * 3)
    assert len(incidents(db)) == 2


def test_every_check_is_stored_in_history(db):
    monitor = make_monitor(db)
    feed(db, monitor, [OK, FAIL, FAIL, FAIL, OK])
    assert len(db.scalars(select(CheckResult)).all()) == 5
