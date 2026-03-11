# Architecture Walkthrough

This document explains the whole TrackMe platform as if you are learning it for the first time.

The easiest way to understand the codebase is to split it into three big parts:

1. the Android app
2. the backend platform
3. the web admin console

Each part has a different job, but all three follow the same product rules:

- visible enrollment
- explicit consent
- lawful location collection
- auditable actions
- no covert surveillance features

## The Big Picture

```text
User / Organization Admin
        |
        v
Android App
  - onboarding and consent
  - local state
  - lawful location signals
  - periodic check-ins
        |
        v
FastAPI Backend
  - auth and tenant checks
  - device registry
  - incident workflows
  - audit logs
  - telemetry ingestion
  - remote action policy
        |
        v
Admin Console
  - device inventory
  - incident views
  - location maps
  - geofences
  - approvals
  - audit viewer
```

## Why the Codebase Is Split This Way

### `app/`

The Android app exists because some things can only happen on the device:

- asking for permission
- showing disclosure text
- reading device-side location signals
- storing local evidence when the network is poor
- scheduling background work using Android-approved APIs

### `backend/`

The backend exists because some rules must be shared and centralized:

- who belongs to which organization
- which incidents exist
- which remote actions are allowed
- which audit records are official
- which telemetry belongs to which device

### `admin-console/`

The admin console exists because human operators need a safe interface.

It should not create secret powers. It should expose controlled backend capabilities in a visible, auditable way.

## System Design Principles

### Visible and consent-based

The system is built for owner-enrolled or organization-managed devices. That means the device should clearly show that it is protected or managed, and background behavior should not silently activate without explicit consent.

### Honest about uncertainty

Location is not treated as magic. The system combines multiple lawful signals and attaches confidence and precision labels so operators can tell the difference between a strong fix and weak fallback evidence.

### Battery-aware

This is especially important for lower-end Android devices and areas with unstable power or network conditions. Normal mode is intentionally conservative. Lost mode escalates, but only for a limited window.

### Audit-first

Sensitive actions such as lost-mode escalation, remote lock, or wipe requests must leave an audit trail. In a real recovery platform, "who did what and why?" matters as much as "did the API work?"

## Android Architecture Style

The Android app uses a practical Clean Architecture layout:

```text
feature/   -> screens and feature-specific UI state
domain/    -> business rules, models, repository contracts, use cases
data/      -> Room, DataStore, network DTOs, repository implementations
location/  -> lawful signal collection and confidence scoring
worker/    -> WorkManager jobs and scheduling
di/        -> Hilt dependency wiring
compliance/-> disclosure and policy-focused text/resources
```

Why this matters for a student:

- `feature/` tells you what the user sees
- `domain/` tells you what the app decides
- `data/` tells you how state is stored or sent
- `worker/` tells you what happens in the background

That separation makes the code easier to test and easier to reason about.

## Backend Architecture Style

The backend uses a service-oriented FastAPI structure:

```text
api/       -> route handlers
schemas/   -> request and response models
services/  -> business logic
db/        -> SQLAlchemy models and DB wiring
core/      -> shared config, auth, security, rate limiting
```

Why this matters:

- route handlers stay thin
- business rules stay in one place
- request validation is explicit
- storage models are separate from API models

## Admin Console Architecture Style

The admin console uses Next.js with typed API and reusable components:

```text
src/app/         -> pages and route layouts
src/components/  -> reusable UI and domain-specific widgets
src/lib/api/     -> typed API client layer
src/lib/mocks/   -> local mock data for development
src/types/       -> shared web-facing models
```

This is useful for a student because it clearly separates:

- routing
- design system components
- API access
- fake data used during local development

## Core Flows

### Enrollment flow

```text
App opens
  -> onboarding screen explains the product
  -> user sees consent and permission education
  -> user enrolls
  -> consent state is stored
  -> check-in scheduling becomes allowed
```

### Normal mode

Normal mode is the default operating state:

- infrequent check-ins
- battery-aware scheduling
- lawful signal collection only
- visible protected state in the UI

### Lost mode

Lost mode is a temporary escalation:

- higher-frequency reporting window
- stronger recovery focus
- incident-linked behavior
- still subject to Android limits
- still visible and auditable

### Incident management

The platform models incidents as a state machine instead of random flags.

Typical states:

- `NORMAL`
- `SUSPECTED_LOST`
- `CONFIRMED_STOLEN`
- `RECOVERED`
- `WIPED`
- `DECOMMISSIONED`

This prevents unsafe jumps and keeps the evidence timeline understandable.

## How Android Background Limits Shape the System

This is one of the most important design lessons in the whole project.

Android does not allow apps to behave like permanent hidden tracking daemons. Background execution and background location are restricted for battery, privacy, and policy reasons.

That is why TrackMe uses:

- WorkManager
- staged permission requests
- low-frequency normal mode
- time-boxed lost mode
- visible consent gating

This is not a workaround. It is the design.

## Why IMEI, IMSI, and Serial Are Not Core

TrackMe does not build its identity model around restricted device identifiers because:

- access is limited on modern Android
- policy expectations are stricter
- they are not necessary for this workflow

Instead, the platform uses:

- enrollment records
- app-managed device IDs
- device key registration
- signed telemetry placeholders
- audit-linked incident history

This is more portable, more privacy-aware, and easier to evolve.

## Why IP and Tower Methods Are Approximate

A student should understand this early:

not all location evidence is equal.

IP-based results often point to:

- a city
- a network region
- a mobile gateway

Tower-based methods estimate from radio infrastructure, not direct GPS position.

That is why TrackMe treats those methods as approximate. They are useful context, but they are not exact recovery coordinates.

## Good Files To Read First

### Android

- [`../app/src/main/java/com/example/trackme/app/TrackMeRootApp.kt`](../app/src/main/java/com/example/trackme/app/TrackMeRootApp.kt)
- [`../app/src/main/java/com/example/trackme/feature/onboarding/OnboardingConsentScreen.kt`](../app/src/main/java/com/example/trackme/feature/onboarding/OnboardingConsentScreen.kt)
- [`../app/src/main/java/com/example/trackme/domain/usecase/PerformCheckInUseCase.kt`](../app/src/main/java/com/example/trackme/domain/usecase/PerformCheckInUseCase.kt)
- [`../app/src/main/java/com/example/trackme/location/LocationFusionEngine.kt`](../app/src/main/java/com/example/trackme/location/LocationFusionEngine.kt)

### Backend

- [`../backend/app/main.py`](../backend/app/main.py)
- [`../backend/app/api/v1/endpoints/platform.py`](../backend/app/api/v1/endpoints/platform.py)
- [`../backend/app/core/security.py`](../backend/app/core/security.py)
- [`../backend/app/services/location_ingestion_service.py`](../backend/app/services/location_ingestion_service.py)

### Admin console

- [`../admin-console/src/app/(dashboard)/devices/page.tsx`](../admin-console/src/app/(dashboard)/devices/page.tsx)
- [`../admin-console/src/app/(dashboard)/map/page.tsx`](../admin-console/src/app/(dashboard)/map/page.tsx)
- [`../admin-console/src/components/common/SensitiveActionModal.tsx`](../admin-console/src/components/common/SensitiveActionModal.tsx)

## Student Mental Model

When you get lost in the repo, ask:

1. Is this code about what the user sees?
2. Is this code about a business rule?
3. Is this code about storage or networking?
4. Is this code about security or policy?

That question usually tells you where to look next.
