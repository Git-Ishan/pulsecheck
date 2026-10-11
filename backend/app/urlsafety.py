import ipaddress
import socket
from urllib.parse import urlsplit

from app import config


class UnsafeURLError(Exception):
    def __init__(self, message: str, kind: str = "blocked_destination"):
        super().__init__(message)
        self.kind = kind


def is_forbidden_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address.split("%")[0])
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped  # ::ffff:127.0.0.1 is really 127.0.0.1
    return (not ip.is_global) or ip.is_multicast


def resolve_host(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    return sorted({info[4][0] for info in infos})


def check_url_allowed(url: str) -> None:
    host = urlsplit(url).hostname
    if not host:
        raise UnsafeURLError("URL has no host")
    try:
        addresses = resolve_host(host)
    except socket.gaierror:
        raise UnsafeURLError("Host could not be resolved", kind="dns_error")
    if config.ALLOW_PRIVATE_TARGETS:
        return
    for address in addresses:
        if is_forbidden_ip(address):
            raise UnsafeURLError("Destination is not allowed")
