import time
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status


class RateLimiter:
    """In-memory sliding-window rate limiter (per client IP).

    Single-process only; for multi-worker production use Redis instead.
    """

    def __init__(self, max_calls: int, period_seconds: float):
        self.max_calls = max_calls
        self.period = period_seconds
        self._hits = defaultdict(deque)

    async def __call__(self, request: Request):
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = self._hits[ip]
        while bucket and bucket[0] <= now - self.period:
            bucket.popleft()
        if len(bucket) >= self.max_calls:
            retry = int(self.period - (now - bucket[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests, slow down",
                headers={"Retry-After": str(retry)},
            )
        bucket.append(now)


login_rate_limit = RateLimiter(max_calls=10, period_seconds=60)
register_rate_limit = RateLimiter(max_calls=5, period_seconds=60)
