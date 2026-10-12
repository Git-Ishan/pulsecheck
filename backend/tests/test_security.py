from app import config, ratelimit
from app.checker import CheckOutcome
from app.ratelimit import SlidingWindowLimiter
from app.routers import monitors as monitors_router

BODY = {"url": "https://example.com"}


def fake_check(monkeypatch):
    async def fake_check_url(url, client):
        return CheckOutcome(True, 200, 5, None)

    monkeypatch.setattr(monitors_router, "check_url", fake_check_url)


# --- API key ---

def test_write_endpoints_require_key(anon_client):
    assert anon_client.post("/monitors", json=BODY).status_code == 401
    assert anon_client.delete("/monitors/1").status_code == 401
    assert anon_client.post("/monitors/1/check").status_code == 401


def test_wrong_key_is_rejected(anon_client):
    response = anon_client.post("/monitors", json=BODY, headers={"X-API-Key": "nope"})
    assert response.status_code == 401


def test_correct_key_is_accepted(client):
    assert client.post("/monitors", json=BODY).status_code == 201


def test_reads_are_public(anon_client):
    assert anon_client.get("/monitors").status_code == 200
    assert anon_client.get("/health").status_code == 200


def test_unconfigured_key_closes_writes(client, monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "")
    response = client.post("/monitors", json=BODY)
    assert response.status_code == 503


def test_rejected_write_creates_nothing(anon_client, client):
    anon_client.post("/monitors", json=BODY)
    assert client.get("/monitors").json() == []


# --- monitor cap ---

def test_monitor_cap(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_MONITORS", 2)
    assert client.post("/monitors", json={"url": "https://a.example.com"}).status_code == 201
    assert client.post("/monitors", json={"url": "https://b.example.com"}).status_code == 201
    assert client.post("/monitors", json={"url": "https://c.example.com"}).status_code == 409


# --- rate limiting ---

def test_limiter_allows_up_to_max_then_rejects():
    limiter = SlidingWindowLimiter(max_calls=2, window_seconds=60)
    assert limiter.check(0.0) == 0.0
    assert limiter.check(1.0) == 0.0
    wait = limiter.check(2.0)
    assert wait > 0
    assert wait <= 60


def test_limiter_recovers_after_the_window():
    limiter = SlidingWindowLimiter(max_calls=1, window_seconds=60)
    assert limiter.check(0.0) == 0.0
    assert limiter.check(30.0) > 0
    assert limiter.check(61.0) == 0.0


def test_manual_check_is_rate_limited(client, monkeypatch):
    fake_check(monkeypatch)
    monkeypatch.setattr(ratelimit, "manual_check_limiter", SlidingWindowLimiter(2, 60))
    monitor_id = client.post("/monitors", json=BODY).json()["id"]

    assert client.post(f"/monitors/{monitor_id}/check").status_code == 200
    assert client.post(f"/monitors/{monitor_id}/check").status_code == 200
    blocked = client.post(f"/monitors/{monitor_id}/check")
    assert blocked.status_code == 429
    assert "retry-after" in blocked.headers


def test_unauthenticated_calls_do_not_use_the_limit(client, anon_client, monkeypatch):
    fake_check(monkeypatch)
    monkeypatch.setattr(ratelimit, "manual_check_limiter", SlidingWindowLimiter(1, 60))
    monitor_id = client.post("/monitors", json=BODY).json()["id"]

    for _ in range(3):
        assert anon_client.post(f"/monitors/{monitor_id}/check").status_code == 401
    assert client.post(f"/monitors/{monitor_id}/check").status_code == 200
