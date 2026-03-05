from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Protocol

from fastapi import HTTPException, Request, status


class RateLimiterBackend(Protocol):
    async def hit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """Returns (allowed, retry_after_seconds)."""


@dataclass
class _Bucket:
    reset_at: float
    count: int


class InMemoryRateLimiter(RateLimiterBackend):
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._buckets: dict[str, _Bucket] = {}

    async def hit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        async with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None or now >= bucket.reset_at:
                bucket = _Bucket(reset_at=now + window_seconds, count=0)
                self._buckets[key] = bucket

            if bucket.count >= limit:
                retry_after = max(1, int(bucket.reset_at - now))
                return False, retry_after

            bucket.count += 1
            return True, 0


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class RateLimiter:
    def __init__(self, backend: RateLimiterBackend) -> None:
        self._backend = backend

    def dependency(self, *, scope: str, limit: int, window_seconds: int):
        async def _dependency(request: Request) -> None:
            key = f"{scope}:{client_ip(request)}"
            allowed, retry_after = await self._backend.hit(key, limit, window_seconds)
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Retry in {retry_after}s",
                    headers={"Retry-After": str(retry_after)},
                )

        return _dependency

