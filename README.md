# TrackMe

TrackMe is an Android-first device recovery and protection platform for organization-owned or explicitly enrolled Android devices.

This project is intentionally not a spyware app. It does not try to hide itself, secretly record people, bypass Android permissions, or depend on restricted device identifiers like IMEI, IMSI, or device serial for its core behavior.

The design goal is simple:

- visible enrollment
- explicit consent
- lawful location collection
- strong audit trails
- realistic recovery workflows

## What This Repository Contains

This repository has three main product surfaces:

- `app/`
  The Android app that runs on the device.
- `backend/`
  The FastAPI backend that stores shared state, enforces security rules, and processes telemetry.
- `admin-console/`
  The Next.js web console used by operators and administrators.

If you are learning the project, think of it like this:

- the Android app gathers lawful device-side evidence
- the backend decides what is allowed and what gets stored
- the admin console shows that information in a controlled interface

## Read This First

The easiest learning path is:

1. [`docs/architecture.md`](./docs/architecture.md)
2. [`docs/android-app.md`](./docs/android-app.md)
3. [`docs/backend.md`](./docs/backend.md)
4. [`docs/location-engine.md`](./docs/location-engine.md)
5. [`docs/security.md`](./docs/security.md)
6. [`docs/testing.md`](./docs/testing.md)
7. [`docs/ownership-enrollment-rbac.md`](./docs/ownership-enrollment-rbac.md)
8. [`docs/compliance-ux.md`](./docs/compliance-ux.md)
9. [`docs/event-queue-rules.md`](./docs/event-queue-rules.md)
10. [`docs/device-identity-signed-telemetry.md`](./docs/device-identity-signed-telemetry.md)
11. [`docs/policy-approvals.md`](./docs/policy-approvals.md)
12. [`docs/device-trust-signals.md`](./docs/device-trust-signals.md)
13. [`docs/operator-support-evidence-exports.md`](./docs/operator-support-evidence-exports.md)
14. [`docs/local-pilot-runbook.md`](./docs/local-pilot-runbook.md)

The larger test execution plan also lives in [`TEST_STRATEGY.md`](./TEST_STRATEGY.md).

## Product Rules

These rules shape both the code and the documentation:

- no stealth tracking
- no hidden activation
- no secret camera, microphone, or screenshot capture
- no bypassing Android or Play policy
- no reliance on IMEI, IMSI, or serial for core identity
- no pretending approximate location is exact
- no background tracking without visible consent

## Beginner-Friendly System Overview

### 1. Android app

The Android app is the visible device client.

Its job is to:

- explain the product clearly
- collect consent
- request permissions in a staged way
- store local device and incident state
- collect lawful location signals
- run scheduled check-ins with WorkManager
- show the user that the device is protected or managed

### 2. Backend

The backend is the shared source of truth.

Its job is to:

- manage tenants, devices, and enrollments
- store telemetry and incident history
- enforce role and tenant checks
- verify signed telemetry placeholders
- record audit logs
- decide whether remote actions are allowed

### 3. Admin console

The admin console is the operator interface.

Its job is to:

- show device inventory
- show incident timelines
- show last known location and confidence
- require confirmation and reason text for sensitive actions
- make operator behavior visible and auditable

## Repository Map

```text
TrackMe/
├── app/                 Android app
├── backend/             FastAPI backend
├── admin-console/       Next.js admin console
├── docs/                Student-friendly architecture guides
├── TEST_STRATEGY.md     Full test planning document
└── README.md            Project entry point
```

## Why Android Background Limits Matter

Android background execution rules are a core design constraint, not a small implementation detail.

That is why the app uses:

- WorkManager instead of covert long-running background loops
- low-frequency normal mode check-ins
- a time-boxed lost mode instead of permanent escalation
- visible foreground/background location permission education

This is both a technical reality and a compliance requirement. A lawful recovery app has to work with Android, not against it.

## Why IMEI, IMSI, and Serial Are Not Core

A beginner may ask:

"Why not identify the device mainly by IMEI or serial number?"

Because that creates more problems than it solves:

- Android restricts access to those identifiers
- Play policy and privacy expectations are stricter around them
- they are not necessary for the actual recovery workflow

TrackMe instead uses:

- explicit enrollment records
- backend-managed device IDs
- consent state
- device key registration
- signed telemetry placeholders
- auditable incident history

This is a more portable and policy-safe design.

## Why IP and Tower Methods Are Approximate

Not every coordinate is equally trustworthy.

For example:

- GPS or fused location can sometimes be precise
- network provider may be less precise
- IP geolocation is often only city-level or region-level
- tower-based estimates are based on radio infrastructure, not direct device position

That is why TrackMe classifies location evidence as:

- `precise`
- `moderate`
- `approximate`

Approximate methods are useful as fallback context, but they must never be marketed as exact recovery coordinates.

## Normal Mode vs Lost Mode

### Normal mode

Normal mode is the default state.

It focuses on:

- lower battery use
- lower bandwidth use
- periodic accountability check-ins

### Lost mode

Lost mode is a temporary escalation for a recovery incident.

It focuses on:

- more frequent check-ins
- stronger location collection attempts within platform limits
- visible incident state
- time-boxed behavior so the device does not remain in permanent high-frequency tracking mode

## Current Code Highlights

### Android app

Important starting points:

- [`app/src/main/java/com/example/trackme/app/TrackMeRootApp.kt`](./app/src/main/java/com/example/trackme/app/TrackMeRootApp.kt)
- [`app/src/main/java/com/example/trackme/feature/onboarding/OnboardingConsentScreen.kt`](./app/src/main/java/com/example/trackme/feature/onboarding/OnboardingConsentScreen.kt)
- [`app/src/main/java/com/example/trackme/feature/enrollment/DeviceEnrollmentScreen.kt`](./app/src/main/java/com/example/trackme/feature/enrollment/DeviceEnrollmentScreen.kt)
- [`app/src/main/java/com/example/trackme/domain/usecase/PerformCheckInUseCase.kt`](./app/src/main/java/com/example/trackme/domain/usecase/PerformCheckInUseCase.kt)
- [`app/src/main/java/com/example/trackme/location/LocationFusionEngine.kt`](./app/src/main/java/com/example/trackme/location/LocationFusionEngine.kt)
- [`app/src/main/java/com/example/trackme/worker/CheckInSchedulerImpl.kt`](./app/src/main/java/com/example/trackme/worker/CheckInSchedulerImpl.kt)

### Backend

Important starting points:

- [`backend/app/main.py`](./backend/app/main.py)
- [`backend/app/api/v1/endpoints/platform.py`](./backend/app/api/v1/endpoints/platform.py)
- [`backend/app/core/security.py`](./backend/app/core/security.py)
- [`backend/app/services/location_ingestion_service.py`](./backend/app/services/location_ingestion_service.py)
- [`backend/app/services/audit_log_service.py`](./backend/app/services/audit_log_service.py)
- [`backend/app/api/v1/endpoints/ownership.py`](./backend/app/api/v1/endpoints/ownership.py)
- [`backend/app/services/ownership_access_service.py`](./backend/app/services/ownership_access_service.py)

### Admin console

Important starting points:

- [`admin-console/src/app/(dashboard)/devices/page.tsx`](./admin-console/src/app/(dashboard)/devices/page.tsx)
- [`admin-console/src/app/(dashboard)/map/page.tsx`](./admin-console/src/app/(dashboard)/map/page.tsx)
- [`admin-console/src/components/common/SensitiveActionModal.tsx`](./admin-console/src/components/common/SensitiveActionModal.tsx)
- [`admin-console/src/lib/api/client.ts`](./admin-console/src/lib/api/client.ts)

## Local Development

For the full integrated local pilot flow, use:

- [`docs/local-pilot-runbook.md`](./docs/local-pilot-runbook.md)

### Android

```bash
./gradlew :app:assembleDebug
./gradlew installDebug
./gradlew testDebugUnitTest
```

Android now reads these Gradle properties:

- `TRACKME_API_BASE_URL`
- `TRACKME_COMMAND_VERIFICATION_PUBLIC_KEY_PEM`
- `TRACKME_MAP_PROVIDER`
- `TRACKME_GOOGLE_STATIC_MAPS_API_KEY`
- `TRACKME_MAPBOX_ACCESS_TOKEN`
- `TRACKME_MAPBOX_USERNAME`
- `TRACKME_MAPBOX_STYLE_ID`

An example file is available at [`gradle.properties.example`](./gradle.properties.example).

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

Backend provider configuration now also includes:

- object storage backend selection for attachments and export bundles
- IP enrichment provider configuration
- integrity verification provider settings
- FCM server credentials

See [`backend/.env.example`](./backend/.env.example) and [`docs/local-pilot-runbook.md`](./docs/local-pilot-runbook.md).

In another terminal, run the queue/rules worker:

```bash
cd backend
source .venv/bin/activate
python -m app.worker
```

The admin console uses the local pilot auth endpoint:

- `POST /api/v1/auth/login`

It expects the bootstrap admin credentials from `backend/.env`.

### Admin console

```bash
cd admin-console
npm install
npm run dev
```

Set `NEXT_PUBLIC_USE_MOCKS=false` so the console uses the live backend by default.

## Current Verification

- Android unit tests pass with `./gradlew testDebugUnitTest`
- Android debug build passes with `./gradlew :app:assembleDebug`
- Backend tests pass with `PYTHONPATH=backend pytest -q backend/tests`
- Admin console typecheck passes with `cd admin-console && npm run typecheck`
- Admin console production build passes with `cd admin-console && npm run build`

## Production Gaps To Understand

This repository already has the right structure, but some security pieces are still placeholders and should be upgraded before production:

- replace placeholder telemetry signing with Android Keystore-backed asymmetric signing
- replace placeholder Play Integrity classification with real server-side verification
- replace development JWT fallback with strict OIDC/JWKS verification in deployed environments
- harden audit storage with stronger database-level immutability controls

## How To Use This Repo As a Student

If you are new to Android and backend systems, use this rule:

- start from the screens and read inward
- then read the use cases
- then read repositories
- then read workers and services

That sequence makes the codebase much easier to understand than jumping straight into low-level details.

## License

No license file is included yet.
