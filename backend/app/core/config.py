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

    fcm_server_key: str | None = None
    fcm_endpoint: str = 'https://fcm.googleapis.com/fcm/send'
    command_signing_secret: str | None = None
    command_default_ttl_minutes: int = 60
    command_max_attempts: int = 5
    command_pending_retry_seconds: int = 300
    geofence_alert_cooldown_seconds: int = 1800
    rules_alert_cooldown_seconds: int = 1800
    incident_offline_threshold_minutes: int = 180
    event_queue_claim_timeout_seconds: int = 120
    event_queue_retry_delay_seconds: int = 30
    event_queue_max_attempts: int = 8
    spatial_default_history_hours: int = 24
    spatial_max_history_hours: int = 168
    exports_storage_dir: str = 'backend/generated_exports'
    observability_bulk_lookup_threshold: int = 10
    observability_failed_auth_threshold: int = 5
    observability_failed_command_threshold: int = 5


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

settings.fcm_server_key = os.getenv('FCM_SERVER_KEY', settings.fcm_server_key)
settings.fcm_endpoint = os.getenv('FCM_ENDPOINT', settings.fcm_endpoint)
settings.command_signing_secret = os.getenv('COMMAND_SIGNING_SECRET', settings.command_signing_secret)
settings.command_default_ttl_minutes = int(os.getenv('COMMAND_DEFAULT_TTL_MINUTES', settings.command_default_ttl_minutes))
settings.command_max_attempts = int(os.getenv('COMMAND_MAX_ATTEMPTS', settings.command_max_attempts))
settings.command_pending_retry_seconds = int(
    os.getenv('COMMAND_PENDING_RETRY_SECONDS', settings.command_pending_retry_seconds)
)
settings.geofence_alert_cooldown_seconds = int(
    os.getenv('GEOFENCE_ALERT_COOLDOWN_SECONDS', settings.geofence_alert_cooldown_seconds)
)
settings.rules_alert_cooldown_seconds = int(
    os.getenv('RULES_ALERT_COOLDOWN_SECONDS', settings.rules_alert_cooldown_seconds)
)
settings.incident_offline_threshold_minutes = int(
    os.getenv('INCIDENT_OFFLINE_THRESHOLD_MINUTES', settings.incident_offline_threshold_minutes)
)
settings.event_queue_claim_timeout_seconds = int(
    os.getenv('EVENT_QUEUE_CLAIM_TIMEOUT_SECONDS', settings.event_queue_claim_timeout_seconds)
)
settings.event_queue_retry_delay_seconds = int(
    os.getenv('EVENT_QUEUE_RETRY_DELAY_SECONDS', settings.event_queue_retry_delay_seconds)
)
settings.event_queue_max_attempts = int(
    os.getenv('EVENT_QUEUE_MAX_ATTEMPTS', settings.event_queue_max_attempts)
)
settings.spatial_default_history_hours = int(
    os.getenv('SPATIAL_DEFAULT_HISTORY_HOURS', settings.spatial_default_history_hours)
)
settings.spatial_max_history_hours = int(
    os.getenv('SPATIAL_MAX_HISTORY_HOURS', settings.spatial_max_history_hours)
)
settings.exports_storage_dir = os.getenv('EXPORTS_STORAGE_DIR', settings.exports_storage_dir)
settings.observability_bulk_lookup_threshold = int(
    os.getenv('OBSERVABILITY_BULK_LOOKUP_THRESHOLD', settings.observability_bulk_lookup_threshold)
)
settings.observability_failed_auth_threshold = int(
    os.getenv('OBSERVABILITY_FAILED_AUTH_THRESHOLD', settings.observability_failed_auth_threshold)
)
settings.observability_failed_command_threshold = int(
    os.getenv('OBSERVABILITY_FAILED_COMMAND_THRESHOLD', settings.observability_failed_command_threshold)
)
