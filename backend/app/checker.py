import asyncio
import time
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from app.urlsafety import UnsafeURLError, check_url_allowed

CHECK_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
MAX_REDIRECTS = 5
REDIRECT_CODES = {301, 302, 303, 307, 308}


@dataclass
class CheckOutcome:
    healthy: bool
    http_status_code: int | None
    response_time_ms: int | None
    error_type: str | None


async def check_url(url: str, client: httpx.AsyncClient) -> CheckOutcome:
    current = url
    total_ms = 0.0

    for hop in range(MAX_REDIRECTS + 1):
        # Validate every hop: DNS can change, and redirects can point inward.
        try:
            await asyncio.to_thread(check_url_allowed, current)
        except UnsafeURLError as exc:
            return CheckOutcome(False, None, None, exc.kind)

        start = time.perf_counter()
        try:
            # stream() reads only the headers; the body is never downloaded.
            async with client.stream("GET", current) as response:
                code = response.status_code
                location = response.headers.get("location")
        except httpx.TimeoutException:
            return CheckOutcome(False, None, None, "timeout")
        except httpx.ConnectError:
            return CheckOutcome(False, None, None, "connection_error")
        except httpx.HTTPError:
            return CheckOutcome(False, None, None, "request_error")
        total_ms += (time.perf_counter() - start) * 1000

        if code in REDIRECT_CODES and location:
            if hop == MAX_REDIRECTS:
                return CheckOutcome(False, code, int(total_ms), "too_many_redirects")
            current = urljoin(current, location)
            continue

        if code < 400:
            return CheckOutcome(True, code, int(total_ms), None)
        return CheckOutcome(False, code, int(total_ms), "http_error")
