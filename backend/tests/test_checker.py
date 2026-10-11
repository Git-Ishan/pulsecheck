import asyncio

import httpx

from app.checker import check_url


def run_check(handler):
    async def go():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await check_url("http://test.local", client)

    return asyncio.run(go())


def test_success_200():
    result = run_check(lambda request: httpx.Response(200))
    assert result.healthy is True
    assert result.http_status_code == 200
    assert result.error_type is None
    assert result.response_time_ms is not None


def test_redirect_is_followed_to_the_final_response():
    def handler(request):
        if request.url.path == "/new":
            return httpx.Response(200)
        return httpx.Response(301, headers={"location": "/new"})

    result = run_check(handler)
    assert result.healthy is True
    assert result.http_status_code == 200


def test_redirect_to_failing_page_is_unhealthy():
    def handler(request):
        if request.url.path == "/new":
            return httpx.Response(500)
        return httpx.Response(301, headers={"location": "/new"})

    result = run_check(handler)
    assert result.healthy is False
    assert result.http_status_code == 500
    assert result.error_type == "http_error"


def test_http_500_is_unhealthy():
    result = run_check(lambda request: httpx.Response(500))
    assert result.healthy is False
    assert result.http_status_code == 500
    assert result.error_type == "http_error"


def test_timeout():
    def handler(request):
        raise httpx.ReadTimeout("too slow", request=request)

    result = run_check(handler)
    assert result.healthy is False
    assert result.http_status_code is None
    assert result.error_type == "timeout"


def test_connection_error():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    result = run_check(handler)
    assert result.healthy is False
    assert result.http_status_code is None
    assert result.error_type == "connection_error"
