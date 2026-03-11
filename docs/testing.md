# Testing Guide

This document explains how to think about testing in TrackMe.

The most important idea is that this platform can fail in more ways than a normal CRUD app.

It can fail by:

- allowing unsafe remote actions
- overstating location precision
- silently enabling tracking
- accepting spoofed telemetry
- allowing cross-tenant access

So the test strategy has to cover correctness, privacy, security, and misuse resistance.

## Testing Layers

## Android unit tests

These test pure Kotlin logic without rendering the full UI.

Good candidates:

- confidence scoring
- spoofing heuristics
- incident state transitions
- remote action rules
- consent gating

Why they matter:

- they run fast
- they are deterministic
- they protect business rules from regressions

Current examples:

- [`LocationConfidenceScorerTest.kt`](../app/src/test/java/com/example/trackme/location/LocationConfidenceScorerTest.kt)
- [`LocationSpoofingDetectorTest.kt`](../app/src/test/java/com/example/trackme/location/LocationSpoofingDetectorTest.kt)
- [`IncidentStateMachineTest.kt`](../app/src/test/java/com/example/trackme/domain/incident/IncidentStateMachineTest.kt)
- [`RequestRemoteActionUseCaseTest.kt`](../app/src/test/java/com/example/trackme/domain/usecase/RequestRemoteActionUseCaseTest.kt)

## ViewModel tests

These test how screen logic reacts to inputs and repository results.

Good candidates:

- onboarding state changes
- enrollment validation
- permission education flows
- incident action success and failure states
- settings toggles and privacy messages

Why they matter:

- UI behavior becomes easier to reason about
- you can verify user-visible states without manual tapping

## Repository tests

These test storage and mapping behavior.

Good candidates:

- Room entity mapping
- DataStore consent persistence
- audit persistence
- location sample persistence
- network-to-domain mapping

Why they matter:

- storage bugs can silently break safety rules
- a bad repository mapping can mislabel precision or consent state

## WorkManager tests

These test background scheduling behavior.

Good candidates:

- normal mode scheduling only happens with consent
- lost mode scheduling respects time-boxing
- delayed wipe runs only when approved and due
- battery and network constraints are set correctly

Why they matter:

- Android background behavior is easy to get wrong
- lawful behavior depends heavily on correct scheduling

## Backend unit tests

These test isolated backend rules.

Good candidates:

- incident state machine transitions
- telemetry signature placeholder verification
- key rotation logic
- suspicious alert generation
- confidence classification logic

Current examples:

- [`test_incident_state_machine.py`](../backend/tests/test_incident_state_machine.py)
- [`test_location_confidence.py`](../backend/tests/test_location_confidence.py)
- [`test_integrity_and_telemetry_security.py`](../backend/tests/test_integrity_and_telemetry_security.py)

## Backend integration tests

These test full request flows through the API.

Good candidates:

- auth required for sensitive endpoints
- wrong role rejected
- wrong tenant resource rejected
- telemetry ingestion writes expected records
- audit verification endpoints behave correctly

Why they matter:

- authorization bugs often only appear in full request flows
- object-level authorization must be tested end to end

## Database and migration tests

These confirm the schema stays safe as the project evolves.

Good candidates:

- migrations apply cleanly from an empty DB
- migrations upgrade a populated DB without data loss
- indexes exist for time-series and geospatial access
- audit tables preserve expected constraints

Why they matter:

- backend correctness depends on schema correctness
- migration failures are expensive to discover late

## Security and authorization tests

These are not optional in this project.

Priority cases:

- missing token is rejected
- invalid token is rejected
- wrong role is rejected
- correct role but wrong tenant resource is rejected
- unmanaged device wipe is rejected
- tampered telemetry is rejected or flagged
- stale or approximate-only evidence stays labeled properly

## False Precision Prevention Tests

This platform must never claim certainty it does not have.

Tests should verify:

- IP-only results remain `approximate`
- stale last known location does not look fresh
- UI badges match backend precision labels
- confidence does not become high when evidence is weak

This is both a correctness issue and a safety issue.

## Poor Network and Offline Tests

TrackMe is designed for environments with intermittent connectivity, so tests should cover:

- offline local capture
- retry on reconnect
- duplicate submission handling
- stale local state
- low-bandwidth loading states in the admin console

This is especially important in real-world recovery scenarios.

## Manual QA Still Matters

Some things are easier to verify on a real device or through hands-on testing:

- permission flows
- visible consent experience
- lost mode UI behavior
- battery impact
- background scheduling behavior
- operator confirmation flows in the admin console

## How a Student Should Decide What To Test

When you change code, ask these questions:

1. What business rule changed?
2. What stored state changed?
3. What visible UI state changed?
4. What privacy or security rule could regress?

Those four questions usually tell you which test layer to update.

## Good Beginner Rule

If the code answers:

- "what should happen?" -> add a unit test
- "what should be stored?" -> add a repository or DB test
- "what should the user see?" -> add a ViewModel or UI test
- "who is allowed?" -> add an authorization test

## Current Baseline

Current automated checks in this repo include:

- Android unit tests with `./gradlew testDebugUnitTest`
- backend tests with `PYTHONPATH=backend pytest -q backend/tests`

The broader planned matrix is documented in [`../TEST_STRATEGY.md`](../TEST_STRATEGY.md).

## Student Takeaway

In this project, a test is not only checking whether the code runs.

It is checking whether the platform stays:

- lawful
- honest about uncertainty
- safe against misuse
- respectful of consent
