from app.state import next_state


def run(start_status, results, threshold=3):
    status, failures = start_status, 0
    events = []
    for healthy in results:
        t = next_state(status, failures, healthy, threshold)
        status, failures = t.status, t.consecutive_failures
        events.append(t.event)
    return status, failures, events


def test_one_failure_does_not_go_down():
    status, failures, events = run("UP", [False])
    assert status == "UP"
    assert failures == 1
    assert events == [None]


def test_three_failures_go_down():
    status, failures, events = run("UP", [False, False, False])
    assert status == "DOWN"
    assert failures == 3
    assert events == [None, None, "went_down"]


def test_continued_failures_do_not_repeat_the_event():
    status, failures, events = run("UP", [False] * 6)
    assert status == "DOWN"
    assert events.count("went_down") == 1


def test_success_after_outage_recovers():
    status, failures, events = run("UP", [False, False, False, True])
    assert status == "UP"
    assert failures == 0
    assert events[-1] == "recovered"


def test_success_resets_the_streak():
    status, failures, events = run("UP", [False, False, True, False])
    assert status == "UP"
    assert failures == 1


def test_unknown_stays_unknown_until_threshold():
    status, failures, events = run("UNKNOWN", [False, False])
    assert status == "UNKNOWN"


def test_first_success_from_unknown_is_up_without_event():
    status, failures, events = run("UNKNOWN", [True])
    assert status == "UP"
    assert events == [None]


def test_stale_streak_is_discarded():
    t = next_state("UP", 2, False, 3, stale=True)
    assert t.status == "UP"
    assert t.consecutive_failures == 1
    assert t.event is None


def test_stale_does_not_clear_an_existing_outage():
    t = next_state("DOWN", 5, False, 3, stale=True)
    assert t.status == "DOWN"
    assert t.event is None
