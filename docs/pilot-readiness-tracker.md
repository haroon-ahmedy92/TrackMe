# Pilot Readiness Tracker

Last updated: 2026-03-25

This tracker is the shared source of truth for the current integration pass that turns TrackMe from a strong demo codebase into a pilot-ready product.

## Complete

- Backend domain coverage for incidents, geofences, case management, approvals, audit, rules, and signed telemetry foundations.
- Android architecture, offline-first telemetry, WorkManager scheduling, Room persistence, and core consent-oriented UX.
- PostGIS-backed geospatial storage and query layer.
- Evidence export bundle generation foundation with CSV/JSON and basic PDF summary support.
- Device identity foundation using Android Keystore-backed signing and backend public-key registration.
- Provider-backed static map rendering on Android and web with precision/freshness labeling and geofence overlays.
- Durable object-storage abstraction for incident attachments and evidence bundles, with local development storage and S3-compatible production wiring.
- Real IP enrichment provider abstraction with cache/rate limiting/fallback behavior and approximate-only labeling.
- Stronger integrity assessment pipeline with verified/advisory/unavailable/suspicious statuses and honest provider messaging.

## Incomplete

- Notification escalation is not fully wired to real recipient/device-token resolution.
- Interactive map SDK adoption is still pending; the current pilot uses real provider-backed static maps rather than full pan/zoom SDK clients.
- Integrity verification is still advisory unless a real Play Integrity verifier is configured upstream.
- Real push notification delivery still depends on valid Firebase project credentials and registered device tokens.
- Android build validation is currently blocked in this sandbox by Gradle runtime/network constraints, even though the Kotlin tree has been updated to match the new abstractions.

## Blocked

- None currently blocked by missing repository context.
- Real push notification delivery still depends on valid Firebase project credentials.
- Interactive map SDK rollout will still depend on provider credentials and mobile/web SDK configuration.

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
- Replaced the web and Android map placeholders with provider-backed Google/Mapbox static map rendering, while preserving fallback rendering and provider abstraction boundaries.
- Replaced placeholder evidence custody with object-storage-backed attachment uploads/downloads and durable export bundle storage metadata.
- Added object storage configuration for local pilot and S3-compatible production deployments.
- Replaced synthetic IP enrichment with a real provider abstraction, cache, rate limiting, and graceful fallback behavior.
- Upgraded integrity assessment from placeholder-only verdict mapping to a structured verified/advisory/unavailable/suspicious pipeline.
- Added environment examples for map providers, storage, IP enrichment, and integrity configuration.

## Current Priority Queue

### Production blockers

1. Complete durable attachment custody/storage beyond placeholder-local behavior.
2. Move from provider-backed static maps to full interactive SDK implementations on Android and web.
3. Configure and verify real IP enrichment and integrity providers in a deployed environment.
4. Strengthen the final local pilot runbook and environment setup for end-to-end stack startup.
5. Validate Android builds in a less restricted environment than this sandbox.

### Pilot blockers

1. Enable real provider credentials for maps, IP enrichment, integrity, and FCM in the pilot environment.
2. Finish remaining live-path docs and setup examples.
3. Tighten remaining operator UX polish and warning cleanup.
4. Decide whether the pilot needs full interactive maps before internet-facing rollout.

### Non-blocking improvements

1. Continue closing production-critical TODO markers in strings/docs/UI copy.
2. Improve operator-facing empty/error/loading states.
3. Expand accessibility/localization coverage across Android and admin console.
