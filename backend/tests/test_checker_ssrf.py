import asyncio
import socket

import httpx

from app import config, urlsafety
from app.checker import check_url


def run(handler, url="http://target.test/"):
    async def go():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await check_url(url, client)

    return asyncio.run(go())


def test_private_destination_is_blocked_and_no_request_is_sent(monkeypatch):
    monkeypatch.setattr(urlsafety, "resolve_host", lambda host: ["10.0.0.5"])
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200)

    result = run(handler)
    assert result.healthy is False
    assert result.error_type == "blocked_destination"
    assert calls == []


def test_dns_rebinding_is_caught_at_check_time(monkeypatch):
    answers = iter([["93.184.216.34"], ["127.0.0.1"]])
    monkeypatch.setattr(urlsafety, "resolve_host", lambda host: next(answers))

    # creation time: the host looks public, so it is accepted
    urlsafety.check_url_allowed("http://rebind.test/")

    # check time: the DNS answer has changed to a private address
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200)

    result = run(handler, "http://rebind.test/")
    assert result.error_type == "blocked_destination"
    assert calls == []


def test_unresolvable_host_is_a_dns_error(monkeypatch):
    def fail(host):
        raise socket.gaierror("no such host")

    monkeypatch.setattr(urlsafety, "resolve_host", fail)
    result = run(lambda request: httpx.Response(200))
    assert result.healthy is False
    assert result.error_type == "dns_error"


def test_private_target_is_checked_when_dev_flag_is_on(monkeypatch):
    monkeypatch.setattr(urlsafety, "resolve_host", lambda host: ["127.0.0.1"])
    monkeypatch.setattr(config, "ALLOW_PRIVATE_TARGETS", True)
    result = run(lambda request: httpx.Response(200))
    assert result.healthy is True


def test_redirect_to_private_address_is_blocked(monkeypatch):
    monkeypatch.setattr(
        urlsafety,
        "resolve_host",
        lambda host: ["127.0.0.1"] if host == "internal.test" else ["93.184.216.34"],
    )
    hosts_called = []

    def handler(request):
        hosts_called.append(request.url.host)
        return httpx.Response(302, headers={"location": "http://internal.test/admin"})

    result = run(handler, "http://start.test/")
    assert result.healthy is False
    assert result.error_type == "blocked_destination"
    assert hosts_called == ["start.test"]  # the internal host was never contacted


def test_redirect_loop_gives_up():
    def handler(request):
        return httpx.Response(302, headers={"location": "/again"})

    result = run(handler)
    assert result.healthy is False
    assert result.error_type == "too_many_redirects"


def test_redirect_to_non_http_scheme_is_blocked():
    def handler(request):
        return httpx.Response(302, headers={"location": "ftp://files.test/secret"})

    result = run(handler)
    assert result.error_type == "blocked_destination"


class ExplodingBody(httpx.AsyncByteStream):
    async def __aiter__(self):
        raise AssertionError("the response body must not be downloaded")
        yield b""


def test_response_body_is_never_downloaded():
    result = run(lambda request: httpx.Response(200, stream=ExplodingBody()))
    assert result.healthy is True
