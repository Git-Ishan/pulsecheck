ALLOWED = "http://localhost:5173"
PREFLIGHT = {
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "x-api-key,content-type",
}


def test_preflight_from_allowed_origin_is_accepted(anon_client):
    response = anon_client.options("/monitors", headers={"Origin": ALLOWED, **PREFLIGHT})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_preflight_from_unknown_origin_is_rejected(anon_client):
    response = anon_client.options(
        "/monitors", headers={"Origin": "http://evil.example", **PREFLIGHT}
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_normal_response_carries_the_allow_header(anon_client):
    response = anon_client.get("/health", headers={"Origin": ALLOWED})
    assert response.headers["access-control-allow-origin"] == ALLOWED
