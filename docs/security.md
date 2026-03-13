# Security Guide

This document explains security and misuse resistance in TrackMe.

A lawful device recovery platform has a different security goal from spyware. The aim is not to create hidden surveillance power. The aim is to protect devices and data while keeping dangerous capabilities visible, controlled, and auditable.

## Security Goals

TrackMe prioritizes:

- visible consent
- tenant isolation
- role-based access control
- tamper-evident audit logging
- careful remote action controls
- honest location precision labeling
- resistance to spoofing and impersonation

## Visible Consent and No Silent Tracking

The first security rule is also a privacy rule:

the app must not silently enable tracking behavior.

That is why TrackMe keeps visible onboarding and explicit consent in the Android app.

Important files:

- [`ConsentDisclosure.kt`](../app/src/main/java/com/example/trackme/compliance/ConsentDisclosure.kt)
- [`TrackingPreferencesDataSource.kt`](../app/src/main/java/com/example/trackme/data/preferences/TrackingPreferencesDataSource.kt)
- [`PerformCheckInUseCase.kt`](../app/src/main/java/com/example/trackme/domain/usecase/PerformCheckInUseCase.kt)
- [`CheckInSchedulerImpl.kt`](../app/src/main/java/com/example/trackme/worker/CheckInSchedulerImpl.kt)

What this means in practice:

- the app icon stays visible
- the user sees disclosure text
- enrollment is explicit
- background check-ins are gated by consent state

## Why IMEI, IMSI, and Serial Are Not Core

TrackMe intentionally avoids building the core identity model around restricted device identifiers.

Reasons:

- Android restricts access to them
- they are privacy-sensitive
- they are not necessary for the workflow

Instead, the design relies on:

- backend device records
- enrollment state
- device keys
- signed telemetry placeholders
- incident and audit history

This is safer and more compliant.

## Enrollment and Locate RBAC

The new ownership flow adds a more specific rule than general JWT role checks:

- `owner`, `admin`, `org_admin`, and `super_admin` are the roles that may reach locate workflows
- `security_operator` may review ownership/access-review records but cannot locate a device by default
- every locate request is audited whether it succeeds or fails

Important files:

- [`ownership.py`](../backend/app/api/v1/endpoints/ownership.py)
- [`ownership_access_service.py`](../backend/app/services/ownership_access_service.py)
- [`DeviceEnrollmentScreen.kt`](../app/src/main/java/com/example/trackme/feature/enrollment/DeviceEnrollmentScreen.kt)

This is important because a security operator role often sounds powerful to beginners, but in this product it is intentionally not a silent tracking role.

## Authentication and Authorization

The backend security helpers live in:

- [`security.py`](../backend/app/core/security.py)

Key ideas:

- callers present bearer tokens
- roles determine what actions are allowed
- tenant checks ensure callers only access their own organization’s records

Important beginner lesson:

authentication means proving identity

authorization means proving permission for the exact action and record

You need both.

## Broken Object-Level Authorization

One of the biggest backend risks is broken object-level authorization, often shortened to BOLA.

That means:

"the caller is authenticated, but they passed the ID of a resource they do not own."

TrackMe hardens against this by checking organization ownership before sensitive actions such as:

- incident transitions
- telemetry ingestion
- remote actions
- audit access

This is one of the most important misuse-resistance controls in the whole backend.

## Signed Telemetry Design

The device should not be trusted just because it sent JSON to the server.

So the architecture includes signed telemetry:

1. the Android app builds a telemetry payload
2. the app computes a payload digest
3. the app attaches a key ID and signature placeholder
4. the backend recomputes the digest
5. the backend checks whether the device key is valid
6. the backend checks whether the signature matches the digest

Important files:

- [`TelemetrySigner.kt`](../app/src/main/java/com/example/trackme/core/TelemetrySigner.kt)
- [`signed_telemetry_service.py`](../backend/app/services/signed_telemetry_service.py)
- [`device_key_service.py`](../backend/app/services/device_key_service.py)

Current state:

- the architecture is present
- the cryptography is still a placeholder

Production direction:

- Android Keystore-backed asymmetric signing
- backend public-key verification
- stronger registration and proof-of-possession

## Play Integrity Placeholder

TrackMe also has a placeholder design for integrity trust.

Important file:

- [`integrity_verification_service.py`](../backend/app/services/integrity_verification_service.py)

Purpose:

- classify the device environment as trusted, unavailable, or untrusted
- feed that signal into suspicious-behavior logic

Current limitation:

- this is not yet real Play Integrity token verification

Production direction:

- verify Play Integrity tokens server-side
- bind requests to nonces
- add replay protection

## Key Registration and Rotation

A serious system needs device key lifecycle management.

TrackMe includes the structure for:

- key registration
- active key lookup
- key rotation
- auditability of key changes

Why this matters:

- keys can expire
- devices can be reprovisioned
- compromised keys may need replacement

Important files:

- [`device_key_service.py`](../backend/app/services/device_key_service.py)
- [`platform.py`](../backend/app/api/v1/endpoints/platform.py)

## Audit Logging and Immutability

Audit logging is not optional in a platform that can lock or wipe devices.

TrackMe records sensitive actions and links them in a tamper-evident chain.

Important files:

- [`audit_log_service.py`](../backend/app/services/audit_log_service.py)
- [`audit_service.py`](../backend/app/services/audit_service.py)

Basic idea:

- each entry stores a previous hash
- a new hash is computed from the event plus the previous link
- the chain can later be verified

This does not make tampering impossible, but it makes tampering much easier to detect.

## Remote Action Controls

Remote actions are powerful and potentially dangerous.

TrackMe restricts them with:

- role checks
- tenant checks
- device capability checks
- elevated confirmation for wipe
- reason capture
- audit logging

There is also an important business tradeoff:

wiping can protect data but reduce the chance of device recovery.

That is why wipe flows require stronger acknowledgement.

## Suspicious Behavior Alerts

The backend can raise suspicious alerts during telemetry ingestion when it sees problems such as:

- unverified telemetry
- digest mismatch
- untrusted integrity result
- approximate-only evidence
- stale samples
- mock-location suspicion

Important file:

- [`location_ingestion_service.py`](../backend/app/services/location_ingestion_service.py)

These alerts do not prove compromise. They tell operators to treat the evidence more carefully.

## Why Privacy and Security Work Together

In this project, privacy guardrails make the system safer.

Examples:

- visible consent reduces abuse
- approximate labels reduce false certainty
- avoiding restricted identifiers lowers privacy risk
- audit logging discourages insider misuse
- time-boxed lost mode reduces long-term tracking exposure

## Current Security Gaps To Know About

A student should understand what is complete and what is still placeholder work.

Still needed before production:

- real OIDC/JWKS verification
- real Android Keystore-backed asymmetric signing
- real Play Integrity token verification
- stronger database-level audit immutability

Understanding these gaps is part of reading the code honestly.

## Student Takeaway

Good security in this platform is not only about stopping outside attackers.

It is also about:

- preventing insider abuse
- preventing silent activation
- preventing false precision
- keeping dangerous actions visible and reviewable
- staying inside Android and Play policy boundaries
