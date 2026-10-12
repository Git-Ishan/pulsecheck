import time
from collections import deque

from fastapi import HTTPException

from app import config


class SlidingWindowLimiter:
    def __init__(self, max_calls: int, window_seconds: float):
        self.max_calls = max_calls
        self.window = window_seconds
        self.calls: deque[float] = deque()

    def check(self, now: float) -> float:
        """Return 0.0 if the call is allowed (and record it), else seconds to wait."""
        while self.calls and now - self.calls[0] >= self.window:
            self.calls.popleft()
        if len(self.calls) >= self.max_calls:
            return self.window - (now - self.calls[0])
        self.calls.append(now)
        return 0.0

    def reset(self) -> None:
        self.calls.clear()


manual_check_limiter = SlidingWindowLimiter(config.MANUAL_CHECK_LIMIT_PER_MINUTE, 60)


def enforce_manual_check_limit() -> None:
    wait = manual_check_limiter.check(time.monotonic())
    if wait > 0:
        raise HTTPException(
            status_code=429,
            detail="Too many manual checks",
            headers={"Retry-After": str(int(wait) + 1)},
        )
