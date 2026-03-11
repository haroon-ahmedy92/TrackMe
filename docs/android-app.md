# Android App Guide

This document explains the Android app in beginner-friendly language.

The Android code lives in [`app/`](../app/). It is the device-side part of the system, so it handles the most sensitive product responsibilities:

- consent
- permissions
- device state
- lawful location collection
- background work
- visible protection status

## What the Android App Is Responsible For

The app does five main jobs:

1. explain the product and collect explicit consent
2. enroll the device in a visible way
3. collect lawful location and device context
4. schedule normal mode and lost mode check-ins
5. keep local state and local audit history

## Package Walkthrough

### `app/`

This package contains the application shell and navigation entry points.

Important files:

- [`TrackMeApplication.kt`](../app/src/main/java/com/example/trackme/TrackMeApplication.kt)
- [`TrackMeRootApp.kt`](../app/src/main/java/com/example/trackme/app/TrackMeRootApp.kt)
- [`AppShellViewModel.kt`](../app/src/main/java/com/example/trackme/app/AppShellViewModel.kt)

Why it exists:

- to start Hilt
- to build the Compose app shell
- to decide whether the user sees onboarding or the main app

### `feature/`

This is the modern screen-focused UI layer.

Important features:

- `onboarding/`
- `enrollment/`
- `home/`
- `status/`
- `lostmode/`
- `map/`
- `incidents/`
- `settings/`
- `audit/`

Why it exists:

- each feature is easier to read in one place
- screen state, screen UI, and ViewModel stay grouped together

### `domain/`

This is the business logic layer.

Important subpackages:

- `model/`
- `repository/`
- `usecase/`
- `incident/`

Why it exists:

- business rules should not depend on Android UI classes
- pure rules are easier to test here

Important files:

- [`PerformCheckInUseCase.kt`](../app/src/main/java/com/example/trackme/domain/usecase/PerformCheckInUseCase.kt)
- [`EnrollDeviceUseCase.kt`](../app/src/main/java/com/example/trackme/domain/usecase/EnrollDeviceUseCase.kt)
- [`SetLostModeUseCase.kt`](../app/src/main/java/com/example/trackme/domain/usecase/SetLostModeUseCase.kt)
- [`ManageIncidentLifecycleUseCase.kt`](../app/src/main/java/com/example/trackme/domain/usecase/ManageIncidentLifecycleUseCase.kt)
- [`IncidentStateMachine.kt`](../app/src/main/java/com/example/trackme/domain/incident/IncidentStateMachine.kt)

### `data/`

This is where the app’s real persistence and network integrations live.

Important subpackages:

- `local/`
  Room database, entities, and DAOs
- `network/`
  Retrofit API and DTO models
- `preferences/`
  DataStore-based preference state
- `repository/`
  implementations of the domain repository interfaces

Why it exists:

- the app needs to store and send data, but the business logic should not care about implementation details

### `location/`

This package contains the location fusion subsystem.

Important files:

- [`LocationFusionEngine.kt`](../app/src/main/java/com/example/trackme/location/LocationFusionEngine.kt)
- [`LocationConfidenceScorer.kt`](../app/src/main/java/com/example/trackme/location/LocationConfidenceScorer.kt)
- [`LocationSpoofingDetector.kt`](../app/src/main/java/com/example/trackme/location/LocationSpoofingDetector.kt)
- [`NetworkContextCollector.kt`](../app/src/main/java/com/example/trackme/location/NetworkContextCollector.kt)
- [`IpApproximateLocationProvider.kt`](../app/src/main/java/com/example/trackme/location/IpApproximateLocationProvider.kt)

Why it exists:

- location logic has enough complexity to deserve its own subsystem
- keeping it separate avoids mixing evidence scoring with UI code

### `worker/`

This package contains WorkManager jobs and scheduling helpers.

Important files:

- [`CheckInSchedulerImpl.kt`](../app/src/main/java/com/example/trackme/worker/CheckInSchedulerImpl.kt)
- [`NormalCheckInWorker.kt`](../app/src/main/java/com/example/trackme/worker/NormalCheckInWorker.kt)
- [`LostModeCheckInWorker.kt`](../app/src/main/java/com/example/trackme/worker/LostModeCheckInWorker.kt)
- [`DelayedWipeWorker.kt`](../app/src/main/java/com/example/trackme/worker/DelayedWipeWorker.kt)

Why it exists:

- Android background work must be carefully scheduled
- WorkManager is the platform-supported way to do deferred and periodic work

### `di/`

This package contains Hilt modules.

Important files:

- [`AppModule.kt`](../app/src/main/java/com/example/trackme/di/AppModule.kt)
- [`DatabaseModule.kt`](../app/src/main/java/com/example/trackme/di/DatabaseModule.kt)
- [`NetworkModule.kt`](../app/src/main/java/com/example/trackme/di/NetworkModule.kt)
- [`BindingModule.kt`](../app/src/main/java/com/example/trackme/di/BindingModule.kt)

Why it exists:

- dependency wiring belongs in one place
- screens and use cases should ask for interfaces, not manually build everything

### `compliance/`

This package holds disclosure-focused content.

Important file:

- [`ConsentDisclosure.kt`](../app/src/main/java/com/example/trackme/compliance/ConsentDisclosure.kt)

Why it exists:

- visible disclosure is a real product requirement, not just UI text
- keeping it centralized makes compliance language easier to review

## How the App Starts

The app launch flow is roughly:

```text
MainActivity
  -> TrackMeRootApp
  -> AppShellViewModel / AppEntryViewModel
  -> decide whether onboarding is still required
  -> show onboarding or main protected app
```

The important lesson is that the app does not assume it can start tracking just because it is installed.

## Consent and Visible Enrollment

The most important product rule on Android is:

the app cannot silently enable tracking behavior.

That is why TrackMe keeps explicit consent separate from simple installation or basic enrollment state.

Important files:

- [`OnboardingConsentScreen.kt`](../app/src/main/java/com/example/trackme/feature/onboarding/OnboardingConsentScreen.kt)
- [`DeviceEnrollmentScreen.kt`](../app/src/main/java/com/example/trackme/feature/enrollment/DeviceEnrollmentScreen.kt)
- [`TrackingPreferencesDataSource.kt`](../app/src/main/java/com/example/trackme/data/preferences/TrackingPreferencesDataSource.kt)

What this means in practice:

- the user sees disclosure text
- the user sees permission education
- the user explicitly confirms enrollment
- the app stores a consent record
- background scheduling depends on that consent record

## Why Enrollment and Consent Are Separate

A student may ask:

"If the device is enrolled, why store another consent flag?"

Because enrollment answers:

"Is this device part of the system?"

Consent answers:

"Is background protection behavior currently allowed?"

Keeping those separate helps prevent silent activation and makes the rules easier to test.

## How Android Background Limits Affect the Design

Android places real limits on:

- background execution
- background location
- long-running services
- battery-intensive work

So the app does not try to act like a hidden tracker.

Instead it uses:

- WorkManager
- explicit permission flows
- periodic work constraints
- low-frequency normal mode
- a temporary lost mode escalation window

This is a core architecture decision, not an implementation detail.

## Normal Mode vs Lost Mode

### Normal mode

Normal mode is the app’s steady-state behavior.

Goals:

- reduce battery use
- reduce data use
- perform basic accountability check-ins

Typical behavior:

- periodic background check-in
- conservative location collection
- battery-not-low and network constraints where appropriate

### Lost mode

Lost mode is the incident-response posture.

Goals:

- improve the chance of recovery
- collect fresher evidence for a limited window
- keep the state visible and auditable

Typical behavior:

- more frequent check-ins
- stronger operator attention
- limited-duration escalation instead of permanent high-frequency tracking

## Why IMEI, IMSI, and Serial Are Not Core

TrackMe does not depend on restricted device identifiers because:

- Android restricts access to them
- they create privacy and policy problems
- they are not required for the recovery workflow

Instead, the app uses:

- app-managed device records
- local enrollment state
- device keys
- backend identity records
- signed telemetry placeholders

This is both cleaner and more compliant.

## How the App Stores Data

### Room

Room is used for structured local state such as:

- location samples
- audit events
- enrollment records
- incident state
- device state

Why Room:

- good typed API
- easy testing
- works well with Flow

### DataStore

DataStore is used for lighter preference-style values such as:

- explicit consent state
- user-facing tracking settings
- scheduling configuration

Why DataStore:

- simple and safe for preference-like state
- asynchronous and coroutine-friendly

## How the App Sends Data

The app uses Retrofit models in `data/network/` to communicate with the backend.

Important files:

- [`RecoveryApi.kt`](../app/src/main/java/com/example/trackme/data/network/RecoveryApi.kt)
- [`NetworkModels.kt`](../app/src/main/java/com/example/trackme/data/network/NetworkModels.kt)
- [`TelemetryPayloads.kt`](../app/src/main/java/com/example/trackme/data/network/TelemetryPayloads.kt)

The important idea for a beginner:

- domain models are what the app wants to talk about
- network models are what the API contract expects

Those do not always have to be identical.

## Location Fusion in Simple Terms

The location engine tries to answer:

"What is the best lawful location evidence we currently have?"

It combines:

- fused GPS/location services
- last known location
- geofence context
- motion/activity context
- network context
- optional backend IP fallback

Then it scores the result and labels its precision.

You can read more in [`location-engine.md`](./location-engine.md).

## Telemetry Signing Placeholder

The app has a placeholder signer in:

- [`TelemetrySigner.kt`](../app/src/main/java/com/example/trackme/core/TelemetrySigner.kt)

This is useful for teaching the shape of the design:

- build payload
- hash payload
- attach key ID
- attach signature placeholder

But it is not production cryptography yet.

## Best Files To Read First

- [`../app/src/main/java/com/example/trackme/app/TrackMeRootApp.kt`](../app/src/main/java/com/example/trackme/app/TrackMeRootApp.kt)
- [`../app/src/main/java/com/example/trackme/feature/onboarding/OnboardingConsentScreen.kt`](../app/src/main/java/com/example/trackme/feature/onboarding/OnboardingConsentScreen.kt)
- [`../app/src/main/java/com/example/trackme/feature/enrollment/EnrollmentViewModel.kt`](../app/src/main/java/com/example/trackme/feature/enrollment/EnrollmentViewModel.kt)
- [`../app/src/main/java/com/example/trackme/domain/usecase/PerformCheckInUseCase.kt`](../app/src/main/java/com/example/trackme/domain/usecase/PerformCheckInUseCase.kt)
- [`../app/src/main/java/com/example/trackme/location/LocationFusionEngine.kt`](../app/src/main/java/com/example/trackme/location/LocationFusionEngine.kt)
- [`../app/src/main/java/com/example/trackme/worker/CheckInSchedulerImpl.kt`](../app/src/main/java/com/example/trackme/worker/CheckInSchedulerImpl.kt)

## Student Takeaway

If you are confused by the number of packages, remember this:

- `feature/` is what the user sees
- `domain/` is what the app decides
- `data/` is how the app stores and sends data
- `location/` is how the app evaluates location evidence
- `worker/` is how the app behaves in the background

That mental model is enough to navigate most of the Android code.
