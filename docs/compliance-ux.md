# Compliance-Oriented UX

This document explains how TrackMe turns privacy and policy requirements into visible user experience.

## Design Goals

The compliance UX is built around a simple rule: users should understand what the product does before they enable anything sensitive.

That leads to these design choices:

- onboarding explains visible enrollment and recovery behavior
- background location is justified as a core recovery feature
- consent is recorded with a version and timestamp
- sensitive actions require reason text and create audit records
- owners and admins can review access history
- retention defaults stay short unless authorized admins change them

## Android App

### Onboarding disclosure

The Android onboarding flow now shows:

- a visible recovery disclosure
- explanation of why foreground and background location may be needed
- what happens if background location is skipped
- a clear path into visible enrollment instead of silent activation

Important files:

- [`app/src/main/java/com/example/trackme/feature/onboarding/OnboardingConsentScreen.kt`](../app/src/main/java/com/example/trackme/feature/onboarding/OnboardingConsentScreen.kt)
- [`app/src/main/java/com/example/trackme/compliance/ConsentDisclosure.kt`](../app/src/main/java/com/example/trackme/compliance/ConsentDisclosure.kt)

### Privacy dashboard

The Android settings/privacy screen now acts as a user-facing compliance center. It shows:

- consent record
- privacy guarantees
- access history summary
- abuse reporting flow
- deprovision request flow

Important files:

- [`app/src/main/java/com/example/trackme/feature/settings/SettingsPrivacyScreen.kt`](../app/src/main/java/com/example/trackme/feature/settings/SettingsPrivacyScreen.kt)
- [`app/src/main/java/com/example/trackme/feature/settings/SettingsPrivacyViewModel.kt`](../app/src/main/java/com/example/trackme/feature/settings/SettingsPrivacyViewModel.kt)

### Lost mode notice

Lost mode now includes a just-in-time explanation before activation. That matters because lost mode changes behavior in a noticeable way:

- more frequent reporting
- still visible to the user
- still limited by Android permissions and policy
- still auditable

Important file:

- [`app/src/main/java/com/example/trackme/feature/lostmode/LostModeScreen.kt`](../app/src/main/java/com/example/trackme/feature/lostmode/LostModeScreen.kt)

## Admin Console

The admin console is where tenant-level compliance controls live.

### Retention policy

Admins can review and change retention windows, but:

- the defaults are intentionally short
- changes require reason entry
- only authorized admin roles can update them
- updates are linked to immutable audit logs

### Device access history

Device detail pages now expose:

- consent/ownership binding information
- reason-required locate actions
- access history for owner/admin review
- deprovision workflow with reason entry

Important files:

- [`admin-console/src/app/(dashboard)/settings/page.tsx`](../admin-console/src/app/(dashboard)/settings/page.tsx)
- [`admin-console/src/app/(dashboard)/devices/[id]/page.tsx`](../admin-console/src/app/(dashboard)/devices/[id]/page.tsx)

## Backend Retention and Audit Linkage

The backend stores tenant-specific retention settings and abuse/deprovision records.

Key behavior:

- every retention change is audited
- every locate request already requires reason text and is audited
- abuse reports are stored and linked into the audit trail
- deprovision actions produce both workflow records and immutable audit entries

Important files:

- [`backend/app/services/compliance_service.py`](../backend/app/services/compliance_service.py)
- [`backend/app/schemas/compliance.py`](../backend/app/schemas/compliance.py)
- [`backend/app/api/v1/endpoints/platform.py`](../backend/app/api/v1/endpoints/platform.py)
- [`backend/app/api/v1/endpoints/ownership.py`](../backend/app/api/v1/endpoints/ownership.py)

## Why This Matters

This project is not trying to hide tracking. The point is the opposite:

- make the managed state visible
- make consent explicit
- explain sensitive features before use
- require reasons for sensitive actions
- give owners and admins a way to review what happened

That is what keeps the system useful for recovery without drifting into deceptive or spyware-like behavior.
