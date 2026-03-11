# TrackMe

TrackMe is an Android-first, lawful, consent-based Device Recovery and Protection platform for organization-owned or explicitly enrolled Android devices.

The project is built around visible enrollment, explicit disclosure, auditable recovery workflows, and policy-safe device management. It is not designed for covert surveillance, hidden activation, or spyware-like behavior.

## What This Repository Contains

- `app/`
  Android app built with Kotlin, Jetpack Compose, Hilt, Room, WorkManager, MVVM/Clean Architecture.
- `backend/`
  FastAPI backend with PostgreSQL + PostGIS, tenant-aware APIs, incident management, location ingestion, and audit logging.
- `admin-console/`
  Next.js + TypeScript web admin console for inventory, incidents, geofences, audit review, and remote action approvals.

## Core Product Principles

- Visible enrollment and explicit consent.
- No stealth tracking.
- No hidden icon behavior.
- No covert screenshots, camera, microphone, or secret recording.
- No restricted identifier dependence for core functionality.
- Approximate location is labeled as approximate.
- Sensitive actions require confirmation and audit reason.

## Current Platform Scope

### Android App

- Onboarding and consent flow.
- Device enrollment flow.
- Home dashboard and protected/managed device state.
- Device status, lost mode, map, incidents, settings, and audit history screens.
- Location fusion engine using lawful signals:
  - fused location
  - last known location
  - geofence context
  - motion context
  - network context
  - optional approximate backend IP fallback
- Battery-aware normal mode and time-boxed lost mode.
- Local append-only audit trail.
- Explicit consent gating for background check-ins and lost-mode scheduling.

### Backend

- Device registry and enrollment services.
- Location ingestion with idempotency.
- Signed telemetry placeholder verification.
- Device key registration and rotation flow.
- Incident lifecycle APIs.
- Remote action request APIs for policy-managed devices only.
- Tenant-aware audit logs with hash chaining and chain verification endpoint.
- Security hardening placeholders for JWT verification and Play Integrity classification.

### Web Admin Console

- Login shell.
- Device inventory and device details.
- Map and last known location view.
- Incident case management.
- Geofence management.
- Audit log viewer.
- Remote action approvals.
- Settings and data retention views.
- Mock API mode for local frontend work.

## Architecture Summary

### Android

- Language: Kotlin
- UI: Jetpack Compose
- DI: Hilt
- Persistence: Room
- Background work: WorkManager
- Networking: Retrofit + Kotlin serialization
- Patterns: MVVM + Clean Architecture

### Backend

- Framework: FastAPI
- Database: PostgreSQL + PostGIS
- Auth: JWT-ready role and tenant checks
- Security: signed telemetry placeholder, audit chain, rate limiting

### Admin Console

- Framework: Next.js App Router
- Language: TypeScript
- UI: custom reusable component system

## Repository Structure

```text
TrackMe/
  app/                 Android client
  backend/             FastAPI backend
  admin-console/       Next.js admin console
  gradle/              Android Gradle wrapper files
  build.gradle.kts     Root Android build config
  settings.gradle.kts  Android module settings
```

## Local Development

### Android App

```bash
./gradlew installDebug
./gradlew testDebugUnitTest
```

Requirements:
- Android Studio
- Android SDK
- USB debugging enabled for on-device testing if using physical hardware

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Or with Docker:

```bash
cd backend
docker compose up --build
```

### Admin Console

```bash
cd admin-console
npm install
npm run dev
```

## Security and Misuse Resistance

- Explicit tracking consent is required before scheduled check-ins run.
- Lost mode is time-boxed and visible in the app workflow.
- Tenant checks are enforced across sensitive backend endpoints.
- Audit logs are hash-chained for tamper evidence.
- Remote wipe requires elevated confirmation and tradeoff acknowledgement.
- Telemetry verification currently uses a placeholder design and must be upgraded before production.
- Play Integrity verification is currently a placeholder assessment path and not final production verification.

## Verification Completed In This Workspace

- Backend tests passing with `PYTHONPATH=backend pytest -q backend/tests`
- Android unit tests passing with `./gradlew testDebugUnitTest`

## Production Readiness Notes

This repository is a strong foundation, but not production-finished. Before production use, the following should be completed:

- Replace placeholder telemetry signing with Android Keystore-backed asymmetric signing.
- Replace placeholder integrity assessment with real Play Integrity server-side verification.
- Replace development JWT fallback with strict OIDC/JWKS verification in all deployed environments.
- Add production deployment, monitoring, and secret management.
- Complete frontend dependency install and backend wiring for the admin console in the target environment.

## License

No license file is currently included in this repository.
