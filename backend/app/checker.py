import time
from dataclasses import dataclass

import httpx

CHECK_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


@dataclass
class CheckOutcome:
    healthy: bool
    http_status_code: int | None
    response_time_ms: int | None
    error_type: str | None


async def check_url(url: str, client: httpx.AsyncClient) -> CheckOutcome:
    start = time.perf_counter()
    try:
        response = await client.get(url)
    except httpx.TimeoutException:
        return CheckOutcome(False, None, None, "timeout")
    except httpx.ConnectError:
        return CheckOutcome(False, None, None, "connection_error")
    except httpx.HTTPError:
        return CheckOutcome(False, None, None, "request_error")

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    code = response.status_code

    if code < 400:
        return CheckOutcome(True, code, elapsed_ms, None)
    return CheckOutcome(False, code, elapsed_ms, "http_error")
