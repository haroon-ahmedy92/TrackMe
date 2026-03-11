from __future__ import annotations

import os

from pydantic import BaseModel, Field


class Settings(BaseModel):

    app_name: str = 'TrackMe Recovery Backend'
    environment: str = 'development'
    api_prefix: str = '/api/v1'

    database_url: str = Field(
        default='postgresql+asyncpg://postgres:postgres@localhost:5432/trackme',
        description='PostgreSQL DSN (async)'
    )
    redis_url: str | None = None

    jwt_issuer: str | None = None
    jwt_audience: str | None = None
    jwt_jwks_url: str | None = None
    jwt_shared_secret: str | None = None
    jwt_algorithms: list[str] = Field(default_factory=lambda: ['HS256'])
    allow_insecure_jwt_for_dev: bool = True

    rate_limit_window_seconds: int = 60
    rate_limit_requests: int = 120


settings = Settings()

# Best-effort env overrides for lightweight local/test execution without pydantic-settings.
settings.database_url = os.getenv('DATABASE_URL', settings.database_url)
settings.redis_url = os.getenv('REDIS_URL', settings.redis_url)
settings.jwt_issuer = os.getenv('JWT_ISSUER', settings.jwt_issuer)
settings.jwt_audience = os.getenv('JWT_AUDIENCE', settings.jwt_audience)
settings.jwt_jwks_url = os.getenv('JWT_JWKS_URL', settings.jwt_jwks_url)
settings.jwt_shared_secret = os.getenv('JWT_SHARED_SECRET', settings.jwt_shared_secret)
settings.jwt_algorithms = [
    item.strip()
    for item in os.getenv('JWT_ALGORITHMS', ','.join(settings.jwt_algorithms)).split(',')
    if item.strip()
]
settings.allow_insecure_jwt_for_dev = os.getenv(
    'ALLOW_INSECURE_JWT_FOR_DEV',
    'true' if settings.allow_insecure_jwt_for_dev else 'false',
).lower() == 'true'
settings.rate_limit_window_seconds = int(os.getenv('RATE_LIMIT_WINDOW_SECONDS', settings.rate_limit_window_seconds))
settings.rate_limit_requests = int(os.getenv('RATE_LIMIT_REQUESTS', settings.rate_limit_requests))
