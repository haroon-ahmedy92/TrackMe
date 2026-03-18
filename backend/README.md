# Device Recovery Platform Backend (FastAPI + PostgreSQL/PostGIS)

Lawful, consent-based backend for owner-enrolled or organization-managed Android device recovery.

## Architecture
- `FastAPI` REST API with OpenAPI docs (`/docs`, `/openapi.json`)
- `PostgreSQL + PostGIS` for relational + geospatial data
- `Redis` optional (ready for distributed rate limit/queue extensions)
- JWT verification support with shared-secret mode and strict tenant role checks
- Tenant-aware data model (`org_id` across platform tables)
- Strong audit chain (`previous_hash`, `event_hash`) for immutable logs
- Idempotent location ingestion (`device_id + idempotency_key`)

## Services Implemented
1. Auth/identity integration placeholders (`/platform/identity/me`)
2. Device registry service (`/platform/devices`)
3. Ownership/enrollment service (`/platform/enrollments`)
4. Location ingestion API with idempotency + signed telemetry verification (`/platform/locations/ingest`)
5. Incident/case management service (`/platform/cases/...`)
6. Rules engine service (`/platform/rules/evaluate`)
7. Audit log service (`/platform/audit-logs`)
   - audit chain verification endpoint (`/platform/audit-logs/verify`)
8. Remote action service (`/platform/remote-actions`)
9. Notification service (`/platform/notifications`)
10. Approximate IP enrichment service (`/platform/ip/enrich`)

## Database Tables
- `users`
- `orgs`
- `devices`
- `enrollments`
- `device_keys`
- `location_events`
- `incidents`
- `incident_events`
- `geofences`
- `remote_actions`
- `audit_logs`
- `notification_events`

Also retained legacy compatibility tables used by earlier scaffold endpoints.

## Local Run (Docker Compose)
```bash
cd backend
docker compose up --build
```

API: `http://localhost:8000`  
Swagger UI: `http://localhost:8000/docs`

## Local Run (without Docker)
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Alembic Migrations
```bash
cd backend
alembic upgrade head
alembic downgrade -1
```

Initial migration:
- creates PostGIS extension
- creates tenant-aware platform tables
- adds geospatial GIST indexes and time-series indexes

## Security and Compliance Notes
- No covert endpoints for hidden capture/surveillance.
- Remote wipe requires elevated confirmation + tradeoff acknowledgement in business rules.
- Telemetry verification supports Android Keystore-backed asymmetric signatures over canonical payload hashes, with an explicit optional/required policy mode.
- A temporary compatibility path still exists for the older placeholder signature format when `ALLOW_PLACEHOLDER_SIGNED_TELEMETRY=true`.
- Device key lifecycle supports key registration, active-key rotation, and revocation (`/platform/device-keys`, `/platform/device-keys/rotate`, `/platform/device-keys/{key_record_id}/revoke`).
- Play Integrity is currently a classification placeholder (`IntegrityVerificationService`) and must be replaced with server-side token verification.
- JWT defaults to verified decode when `JWT_SHARED_SECRET` is configured. Insecure unverified token mode is allowed only when explicitly enabled for development.
- Rate limiting middleware is in-memory (swap to Redis-backed limiter in multi-node production).

## Testing
```bash
cd backend
PYTHONPATH=. pytest -q
```
