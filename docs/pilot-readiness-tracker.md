# Pilot Readiness Tracker

Last updated: 2026-03-24

This tracker is the shared source of truth for the current integration pass that turns TrackMe from a strong demo codebase into a pilot-ready product.

## Complete

- Backend domain coverage for incidents, geofences, case management, approvals, audit, rules, and signed telemetry foundations.
- Android architecture, offline-first telemetry, WorkManager scheduling, Room persistence, and core consent-oriented UX.
- PostGIS-backed geospatial storage and query layer.
- Evidence export bundle generation foundation with CSV/JSON and basic PDF summary support.
- Device identity foundation using Android Keystore-backed signing and backend public-key registration.

## Incomplete

- Notification escalation is not fully wired to real recipient/device-token resolution.
- Evidence attachment custody still relies on placeholder storage behavior unless explicitly supplied.
- Map rendering still needs real provider-backed implementations on Android and web.
- Integrity and IP enrichment still contain placeholder/advisory paths.
- Evidence attachment custody still relies on local filesystem/object-storage placeholder behavior.
- Real provider-backed maps, IP enrichment, and integrity verification are still pending.

## Blocked

- None currently blocked by missing repository context.
- Real push notification delivery still depends on valid Firebase project credentials.
- Real map rendering will depend on provider credentials and SDK configuration.

## Fixed In This Pass

- Added a shared readiness tracker document.
- Stabilized the admin console so current UI edits typecheck and build again:
  - fixed `Card` `className` typing mismatch
  - fixed unused imports and const/lint issues
  - ignored generated `tsconfig.tsbuildinfo`
  - added a separate typecheck config for stricter CI-friendly validation
- Switched the admin console to live API mode by default, with mock mode only behind explicit config.
- Replaced the Android hardcoded backend URL with `BuildConfig`-driven environment configuration for local/dev use.
- Added local pilot admin authentication for the web console against the FastAPI backend.
- Hardened backend defaults for local pilots and non-dev environments:
  - insecure JWT fallback disabled by default
  - signed telemetry required by default
  - placeholder signed telemetry disabled by default
- Replaced placeholder command-signing secrets with key-based ECDSA command signatures and Android verification.
- Added a real operator enrollment issuance flow to the support dashboard using `/api/v1/ownership/pairing-tokens`.
- Added a runnable event queue/rules worker process and Docker Compose worker service.
- Removed fake incident notification tokens and replaced them with explicit internal escalation alerts.
- Replaced silent FCM no-op behavior with explicit failure logging and failed notification records.
- Added recent notification/escalation visibility to the operator support dashboard.

## Current Priority Queue

### Production blockers

1. Complete durable attachment custody/storage beyond placeholder-local behavior.
2. Replace placeholder map rendering with provider-backed implementations on Android and web.
3. Replace synthetic IP enrichment and placeholder integrity verification with configurable real integrations.
4. Strengthen the final local pilot runbook and environment setup for end-to-end stack startup.
5. Reduce remaining operator-facing warnings/noise in the admin console build output.

### Pilot blockers

1. Wire attachment storage to a durable abstraction suitable for pilot evidence handling.
2. Add provider-backed maps for Android and web.
3. Replace synthetic IP enrichment and placeholder integrity flows with configurable real integrations.
4. Finish remaining live-path docs and setup examples.
5. Tighten remaining operator UX polish and warning cleanup.

### Non-blocking improvements

1. Continue closing production-critical TODO markers in strings/docs/UI copy.
2. Improve operator-facing empty/error/loading states.
3. Expand accessibility/localization coverage across Android and admin console.
