import socket

import pytest

from app import config, urlsafety
from app.urlsafety import UnsafeURLError, check_url_allowed, is_forbidden_ip


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.5",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",  # cloud metadata
        "100.64.0.1",
        "0.0.0.0",
        "224.0.0.1",
        "::1",
        "fe80::1",
        "fc00::1",
        "::ffff:127.0.0.1",
    ],
)
def test_forbidden_addresses(address):
    assert is_forbidden_ip(address) is True


@pytest.mark.parametrize(
    "address", ["93.184.216.34", "8.8.8.8", "2606:2800:220:1:248:1893:25c8:1946"]
)
def test_public_addresses_are_allowed(address):
    assert is_forbidden_ip(address) is False


def test_public_host_is_allowed():
    check_url_allowed("https://example.com/")  # fake DNS returns a public IP


def test_hostname_resolving_to_private_ip_is_rejected(monkeypatch):
    monkeypatch.setattr(urlsafety, "resolve_host", lambda host: ["127.0.0.1"])
    with pytest.raises(UnsafeURLError):
        check_url_allowed("https://innocent-looking.example.com/")


def test_one_private_address_among_many_is_rejected(monkeypatch):
    monkeypatch.setattr(
        urlsafety, "resolve_host", lambda host: ["93.184.216.34", "10.0.0.5"]
    )
    with pytest.raises(UnsafeURLError):
        check_url_allowed("https://mixed.example.com/")


def test_unresolvable_host_is_rejected(monkeypatch):
    def fail(host):
        raise socket.gaierror("no such host")

    monkeypatch.setattr(urlsafety, "resolve_host", fail)
    with pytest.raises(UnsafeURLError):
        check_url_allowed("https://does-not-exist.example.com/")


def test_private_targets_can_be_allowed_for_local_dev(monkeypatch):
    monkeypatch.setattr(urlsafety, "resolve_host", lambda host: ["127.0.0.1"])
    monkeypatch.setattr(config, "ALLOW_PRIVATE_TARGETS", True)
    check_url_allowed("http://localhost:8000/health")


# --- through the real API ---

def test_api_rejects_metadata_address(client, monkeypatch):
    monkeypatch.setattr(urlsafety, "resolve_host", lambda host: ["169.254.169.254"])
    response = client.post("/monitors", json={"url": "http://169.254.169.254/latest/meta-data"})
    assert response.status_code == 422


def test_api_rejects_localhost(client, monkeypatch):
    monkeypatch.setattr(urlsafety, "resolve_host", lambda host: ["127.0.0.1"])
    response = client.post("/monitors", json={"url": "http://localhost:8000/health"})
    assert response.status_code == 422
    assert client.get("/monitors").json() == []


def test_api_accepts_public_url(client):
    response = client.post("/monitors", json={"url": "https://example.com"})
    assert response.status_code == 201


def test_non_http_scheme_is_rejected():
    with pytest.raises(UnsafeURLError):
        check_url_allowed("ftp://example.com/file")
