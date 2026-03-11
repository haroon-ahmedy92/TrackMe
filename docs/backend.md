# Backend Guide

This document explains the FastAPI backend in a beginner-friendly way.

The backend lives in [`backend/`](../backend/). Its job is to act as the shared source of truth for organizations, devices, incidents, telemetry, geofences, remote actions, and audit records.

## Why the Backend Exists

You cannot build a serious device recovery platform with only an on-device app.

The backend is needed for:

- shared device inventory
- multi-user access
- organization and tenant separation
- incident timelines
- remote action approvals
- audit logging
- telemetry validation

Think of it like this:

- the phone knows what happened locally
- the backend knows what the whole organization is allowed to do

## Folder Walkthrough

### `app/main.py`

This is the application entry point.

Why it exists:

- creates the FastAPI app
- wires the routers
- exposes OpenAPI docs and runtime configuration

### `app/api/`

This is the route layer.

Important files:

- [`api/v1/router.py`](../backend/app/api/v1/router.py)
- [`api/v1/endpoints/platform.py`](../backend/app/api/v1/endpoints/platform.py)
- [`api/v1/endpoints/devices.py`](../backend/app/api/v1/endpoints/devices.py)
- [`api/v1/endpoints/telemetry.py`](../backend/app/api/v1/endpoints/telemetry.py)
- [`api/v1/endpoints/actions.py`](../backend/app/api/v1/endpoints/actions.py)
- [`api/v1/endpoints/audit.py`](../backend/app/api/v1/endpoints/audit.py)

Why it exists:

- receives HTTP requests
- authenticates and authorizes callers
- validates input
- hands real business work to services

Important lesson:

route files should stay thin. If a route contains lots of decision logic, it usually belongs in a service instead.

### `app/schemas/`

This package contains typed request and response models.

Examples:

- `LocationIngestRequest`
- `IncidentTransitionRequest`
- `DeviceKeyRegisterRequest`

Why it exists:

- API contracts should be explicit
- validation should be central, not hand-written in every route
- OpenAPI docs become clearer

### `app/services/`

This is the main business-logic layer.

Important services:

- `device_registry_service.py`
- `enrollment_service.py`
- `device_key_service.py`
- `location_ingestion_service.py`
- `incident_service.py`
- `case_management_service.py`
- `rules_engine_service.py`
- `remote_action_service.py`
- `notification_service.py`
- `audit_log_service.py`
- `signed_telemetry_service.py`
- `integrity_verification_service.py`
- `ip_enrichment_service.py`

Why it exists:

- routes should not carry all the platform rules
- the same rules may be needed by multiple endpoints
- services are easier to test

### `app/db/`

This package contains database models and setup.

Important file:

- [`models.py`](../backend/app/db/models.py)

Why it exists:

- database structure should be explicit
- SQLAlchemy models support migrations and queries
- storage concerns should be separate from API schema concerns

### `app/core/`

This package holds shared infrastructure:

- configuration
- authentication helpers
- authorization helpers
- rate limiting

Important files:

- [`config.py`](../backend/app/core/config.py)
- [`security.py`](../backend/app/core/security.py)
- [`rate_limit.py`](../backend/app/core/rate_limit.py)

Why it exists:

- security and configuration rules should not be duplicated across route files

## What the Backend Actually Does

## Device registry

The backend stores the official record of devices known to an organization.

That includes things like:

- device IDs
- enrollment state
- last check-in
- online/offline status
- management capabilities

## Enrollment and ownership

The backend decides which organization a device belongs to and who is allowed to manage it.

This is important because device recovery is not just about location. It is also about ownership and authorization.

## Incident lifecycle

The backend models incidents as a state machine instead of a loose collection of flags.

Typical states:

- `NORMAL`
- `SUSPECTED_LOST`
- `CONFIRMED_STOLEN`
- `RECOVERED`
- `WIPED`
- `DECOMMISSIONED`

Why this matters:

- it prevents invalid transitions
- it makes auditing easier
- it keeps incident rules testable

## Telemetry ingestion

The backend receives device telemetry and checks:

- does this device belong to the right tenant?
- is the payload shape valid?
- does the payload digest match?
- is the telemetry signature placeholder valid?
- does the integrity verdict look trusted, untrusted, or unavailable?
- does the sample look suspicious?

This logic mainly lives in:

- [`location_ingestion_service.py`](../backend/app/services/location_ingestion_service.py)
- [`signed_telemetry_service.py`](../backend/app/services/signed_telemetry_service.py)
- [`integrity_verification_service.py`](../backend/app/services/integrity_verification_service.py)

## Geofences and rules

The backend stores geofences and can trigger rule-based alerts when a device leaves or enters expected areas.

This is useful for asset protection, but it is still opt-in and must stay visibly managed.

## Remote actions

The backend handles sensitive actions such as lock or wipe requests.

Important rules:

- only allowed roles can request them
- the target device must belong to the caller’s organization
- extra confirmation is required for wipe
- reasons must be recorded
- all steps are audited

This is deliberate. A lawful recovery platform should not casually expose destructive power.

## Audit logging

Audit records are a core security feature, not just a debugging aid.

The backend stores:

- who triggered an action
- what action happened
- when it happened
- why it happened, where relevant
- how it links to previous audit entries

TrackMe uses a tamper-evident hash chain so audit entries are harder to alter without detection.

## Tenant-Aware Design

This is one of the most important ideas in the backend.

TrackMe is multi-tenant, which means more than one organization can use the same platform. Because of that, almost every sensitive record must be scoped to an organization.

For a beginner, this is the rule to remember:

authentication asks "who are you?"

authorization asks "are you allowed to do this to this specific record?"

That second question is where broken object-level authorization bugs happen.

## Why IP-Based Location Stays Approximate

The backend has an approximate IP enrichment path. This is useful when the app cannot provide a strong device-side location fix.

But IP geolocation is not exact because:

- a public IP may represent many devices
- mobile traffic may route through distant gateways
- city-level or region-level estimates are common

That is why the system must preserve the label `approximate`.

## Signed Telemetry and Key Rotation

The backend is designed around a stronger long-term trust model:

- a device registers a key
- the device signs telemetry
- the backend checks the key and payload digest
- keys can rotate over time

Current state:

- the structure exists
- the crypto implementation is still a placeholder

Production direction:

- Android Keystore-backed asymmetric keys
- backend public-key verification
- stronger proof-of-possession flows

## Good Files To Read First

- [`../backend/app/main.py`](../backend/app/main.py)
- [`../backend/app/api/v1/endpoints/platform.py`](../backend/app/api/v1/endpoints/platform.py)
- [`../backend/app/core/security.py`](../backend/app/core/security.py)
- [`../backend/app/db/models.py`](../backend/app/db/models.py)
- [`../backend/app/services/location_ingestion_service.py`](../backend/app/services/location_ingestion_service.py)
- [`../backend/app/services/device_key_service.py`](../backend/app/services/device_key_service.py)
- [`../backend/app/services/audit_log_service.py`](../backend/app/services/audit_log_service.py)

## Student Mental Model

If you are learning FastAPI, use this simple map:

- routes answer: "which URL handles this request?"
- schemas answer: "what data shape is allowed?"
- services answer: "what should happen?"
- DB models answer: "what gets stored?"

That model is enough to start reading the backend with confidence.
