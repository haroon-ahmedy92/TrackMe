from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.http_compression import GzipRequestMiddleware
from app.core.observability import StructuredRequestLogMiddleware
from app.core.rate_limit import InMemoryRateLimitMiddleware

app = FastAPI(
    title=settings.app_name,
    description='Lawful, consent-based device recovery backend for enrolled and organization-managed Android devices.',
    version='0.1.0',
)
app.add_middleware(GzipRequestMiddleware)
app.add_middleware(
    InMemoryRateLimitMiddleware,
    requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
app.add_middleware(StructuredRequestLogMiddleware)
app.include_router(v1_router, prefix=settings.api_prefix)
