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
    allow_insecure_jwt_for_dev: bool = False
    local_auth_enabled: bool = False
    pilot_bootstrap_org_id: str | None = None
    pilot_bootstrap_org_slug: str = 'pilot-org'
    pilot_bootstrap_org_name: str = 'TrackMe Pilot'
    pilot_bootstrap_admin_email: str | None = None
    pilot_bootstrap_admin_password: str | None = None
    pilot_bootstrap_admin_name: str = 'Pilot Admin'
    pilot_bootstrap_admin_role: str = 'admin'

    rate_limit_window_seconds: int = 60
    rate_limit_requests: int = 120

    fcm_server_key: str | None = None
    fcm_endpoint: str = 'https://fcm.googleapis.com/fcm/send'
    command_signing_private_key_pem: str | None = None
    command_signing_public_key_pem: str | None = None
    command_signing_private_key_path: str | None = None
    command_signing_public_key_path: str | None = None
    allow_placeholder_command_signing_for_dev: bool = False
    worker_poll_interval_seconds: float = 2.0
    worker_idle_sleep_seconds: float = 2.0
    worker_max_events_per_tick: int = 100
    worker_name: str = 'trackme-rules-worker'
    command_default_ttl_minutes: int = 60
    command_max_attempts: int = 5
    command_pending_retry_seconds: int = 300
    signed_telemetry_mode: str = 'required'
    allow_placeholder_signed_telemetry: bool = False
    geofence_alert_cooldown_seconds: int = 1800
    rules_alert_cooldown_seconds: int = 1800
    incident_offline_threshold_minutes: int = 180
    event_queue_claim_timeout_seconds: int = 120
    event_queue_retry_delay_seconds: int = 30
    event_queue_max_attempts: int = 8
    spatial_default_history_hours: int = 24
    spatial_max_history_hours: int = 168
    exports_storage_dir: str = 'backend/generated_exports'
    object_storage_backend: str = 'local'
    object_storage_local_dir: str = 'backend/object_storage'
    object_storage_s3_bucket: str | None = None
    object_storage_s3_region: str | None = None
    object_storage_s3_endpoint: str | None = None
    object_storage_s3_access_key: str | None = None
    object_storage_s3_secret_key: str | None = None
    object_storage_s3_prefix: str = 'trackme'
    ip_enrichment_provider: str = 'none'
    ip_enrichment_api_url: str | None = None
    ip_enrichment_api_key: str | None = None
    ip_enrichment_cache_ttl_seconds: int = 21600
    integrity_verification_provider: str = 'none'
    play_integrity_expected_package: str | None = None
    observability_bulk_lookup_threshold: int = 10
    observability_failed_auth_threshold: int = 5
    observability_failed_command_threshold: int = 5
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ['http://localhost:3000', 'http://127.0.0.1:3000']
    )


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
settings.local_auth_enabled = os.getenv(
    'LOCAL_AUTH_ENABLED',
    'true' if settings.local_auth_enabled else 'false',
).lower() == 'true'
settings.pilot_bootstrap_org_id = os.getenv('PILOT_BOOTSTRAP_ORG_ID', settings.pilot_bootstrap_org_id)
settings.pilot_bootstrap_org_slug = os.getenv('PILOT_BOOTSTRAP_ORG_SLUG', settings.pilot_bootstrap_org_slug)
settings.pilot_bootstrap_org_name = os.getenv('PILOT_BOOTSTRAP_ORG_NAME', settings.pilot_bootstrap_org_name)
settings.pilot_bootstrap_admin_email = os.getenv(
    'PILOT_BOOTSTRAP_ADMIN_EMAIL',
    settings.pilot_bootstrap_admin_email,
)
settings.pilot_bootstrap_admin_password = os.getenv(
    'PILOT_BOOTSTRAP_ADMIN_PASSWORD',
    settings.pilot_bootstrap_admin_password,
)
settings.pilot_bootstrap_admin_name = os.getenv(
    'PILOT_BOOTSTRAP_ADMIN_NAME',
    settings.pilot_bootstrap_admin_name,
)
settings.pilot_bootstrap_admin_role = os.getenv(
    'PILOT_BOOTSTRAP_ADMIN_ROLE',
    settings.pilot_bootstrap_admin_role,
).lower()
settings.rate_limit_window_seconds = int(os.getenv('RATE_LIMIT_WINDOW_SECONDS', settings.rate_limit_window_seconds))
settings.rate_limit_requests = int(os.getenv('RATE_LIMIT_REQUESTS', settings.rate_limit_requests))

settings.fcm_server_key = os.getenv('FCM_SERVER_KEY', settings.fcm_server_key)
settings.fcm_endpoint = os.getenv('FCM_ENDPOINT', settings.fcm_endpoint)
settings.command_signing_private_key_pem = os.getenv(
    'COMMAND_SIGNING_PRIVATE_KEY_PEM',
    settings.command_signing_private_key_pem,
)
settings.command_signing_public_key_pem = os.getenv(
    'COMMAND_SIGNING_PUBLIC_KEY_PEM',
    settings.command_signing_public_key_pem,
)
settings.command_signing_private_key_path = os.getenv(
    'COMMAND_SIGNING_PRIVATE_KEY_PATH',
    settings.command_signing_private_key_path,
)
settings.command_signing_public_key_path = os.getenv(
    'COMMAND_SIGNING_PUBLIC_KEY_PATH',
    settings.command_signing_public_key_path,
)
settings.allow_placeholder_command_signing_for_dev = os.getenv(
    'ALLOW_PLACEHOLDER_COMMAND_SIGNING_FOR_DEV',
    'true' if settings.allow_placeholder_command_signing_for_dev else 'false',
).lower() == 'true'
settings.command_default_ttl_minutes = int(os.getenv('COMMAND_DEFAULT_TTL_MINUTES', settings.command_default_ttl_minutes))
settings.command_max_attempts = int(os.getenv('COMMAND_MAX_ATTEMPTS', settings.command_max_attempts))
settings.command_pending_retry_seconds = int(
    os.getenv('COMMAND_PENDING_RETRY_SECONDS', settings.command_pending_retry_seconds)
)
settings.signed_telemetry_mode = os.getenv('SIGNED_TELEMETRY_MODE', settings.signed_telemetry_mode).lower()
settings.allow_placeholder_signed_telemetry = os.getenv(
    'ALLOW_PLACEHOLDER_SIGNED_TELEMETRY',
    'true' if settings.allow_placeholder_signed_telemetry else 'false',
).lower() == 'true'
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
settings.object_storage_backend = os.getenv('OBJECT_STORAGE_BACKEND', settings.object_storage_backend).lower()
settings.object_storage_local_dir = os.getenv('OBJECT_STORAGE_LOCAL_DIR', settings.object_storage_local_dir)
settings.object_storage_s3_bucket = os.getenv('OBJECT_STORAGE_S3_BUCKET', settings.object_storage_s3_bucket)
settings.object_storage_s3_region = os.getenv('OBJECT_STORAGE_S3_REGION', settings.object_storage_s3_region)
settings.object_storage_s3_endpoint = os.getenv('OBJECT_STORAGE_S3_ENDPOINT', settings.object_storage_s3_endpoint)
settings.object_storage_s3_access_key = os.getenv('OBJECT_STORAGE_S3_ACCESS_KEY', settings.object_storage_s3_access_key)
settings.object_storage_s3_secret_key = os.getenv('OBJECT_STORAGE_S3_SECRET_KEY', settings.object_storage_s3_secret_key)
settings.object_storage_s3_prefix = os.getenv('OBJECT_STORAGE_S3_PREFIX', settings.object_storage_s3_prefix)
settings.ip_enrichment_provider = os.getenv('IP_ENRICHMENT_PROVIDER', settings.ip_enrichment_provider).lower()
settings.ip_enrichment_api_url = os.getenv('IP_ENRICHMENT_API_URL', settings.ip_enrichment_api_url)
settings.ip_enrichment_api_key = os.getenv('IP_ENRICHMENT_API_KEY', settings.ip_enrichment_api_key)
settings.ip_enrichment_cache_ttl_seconds = int(
    os.getenv('IP_ENRICHMENT_CACHE_TTL_SECONDS', settings.ip_enrichment_cache_ttl_seconds)
)
settings.integrity_verification_provider = os.getenv(
    'INTEGRITY_VERIFICATION_PROVIDER',
    settings.integrity_verification_provider,
).lower()
settings.play_integrity_expected_package = os.getenv(
    'PLAY_INTEGRITY_EXPECTED_PACKAGE',
    settings.play_integrity_expected_package,
)
settings.observability_bulk_lookup_threshold = int(
    os.getenv('OBSERVABILITY_BULK_LOOKUP_THRESHOLD', settings.observability_bulk_lookup_threshold)
)
settings.observability_failed_auth_threshold = int(
    os.getenv('OBSERVABILITY_FAILED_AUTH_THRESHOLD', settings.observability_failed_auth_threshold)
)
settings.observability_failed_command_threshold = int(
    os.getenv('OBSERVABILITY_FAILED_COMMAND_THRESHOLD', settings.observability_failed_command_threshold)
)
settings.cors_allowed_origins = [
    item.strip()
    for item in os.getenv('CORS_ALLOWED_ORIGINS', ','.join(settings.cors_allowed_origins)).split(',')
    if item.strip()
]
