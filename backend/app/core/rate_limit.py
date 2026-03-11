from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests: int, window_seconds: int) -> None:
        super().__init__(app)
        self.requests = requests
        self.window_seconds = window_seconds
        self._hits: dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path.endswith('/health'):
            return await call_next(request)

        now = time.time()
        key = self._key(request)
        hit_times = self._hits[key]
        while hit_times and (now - hit_times[0]) > self.window_seconds:
            hit_times.popleft()

        if len(hit_times) >= self.requests:
            return JSONResponse(
                status_code=429,
                content={
                    'detail': 'Rate limit exceeded',
                    'limit': self.requests,
                    'window_seconds': self.window_seconds,
                },
            )

        hit_times.append(now)
        return await call_next(request)

    def _key(self, request: Request) -> str:
        forwarded = request.headers.get('x-forwarded-for')
        ip = forwarded.split(',')[0].strip() if forwarded else (request.client.host if request.client else 'unknown')
        return f'{ip}:{request.url.path}'
