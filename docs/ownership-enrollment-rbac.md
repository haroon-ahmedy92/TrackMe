# Enrollment, Ownership, and RBAC Guide

This guide explains the new enrollment and access-control system that binds a phone to an owner or organization in an explicit, auditable way.

## What Problem This Solves

The older Android MVP had a simple local enrollment flag. That was enough to unlock the rest of the app, but it was not enough for a real platform because it did not answer these questions clearly:

- who is allowed to enroll this device?
- who owns the device after enrollment?
- who can locate it?
- how is that decision audited?
- how do we transfer ownership later?

The new flow adds those answers on both Android and the backend.

## Android Flow

Important files:

- [`DeviceEnrollmentScreen.kt`](../app/src/main/java/com/example/trackme/feature/enrollment/DeviceEnrollmentScreen.kt)
- [`EnrollmentViewModel.kt`](../app/src/main/java/com/example/trackme/feature/enrollment/EnrollmentViewModel.kt)
- [`EnrollmentCoordinator.kt`](../app/src/main/java/com/example/trackme/feature/enrollment/EnrollmentCoordinator.kt)
- [`EnrollmentRepositoryImpl.kt`](../app/src/main/java/com/example/trackme/data/repository/EnrollmentRepositoryImpl.kt)
- [`DeviceKeyMaterialGenerator.kt`](../app/src/main/java/com/example/trackme/core/security/DeviceKeyMaterialGenerator.kt)

The device-side flow is now:

```text
Onboarding consent
  -> visible permission education
  -> explicit consent checkbox
  -> enrollment screen
     -> choose ownership type
     -> choose authorization role context
     -> paste enrollment token or QR/link payload
     -> generate/load device keypair
     -> call backend pairing endpoint
     -> save local enrollment state
     -> show managed/protected app shell
```

Important design choices:

- The app never hides itself.
- The device user sees ownership type and pairing method before enrollment completes.
- The app stores whether backend verification succeeded or is still pending.
- If the backend is temporarily unreachable, the app can still save a local pending state instead of pretending verification already happened.

## Ownership Model

The backend supports two ownership modes:

- `SINGLE_USER`
  One specific user is bound as the owner.
- `ORGANIZATION_OWNED`
  The device belongs to the organization rather than an individual owner account.

Ownership is stored in `device_ownership_bindings` and is not mixed into random metadata fields.

Why this matters:

- locate permissions can be different for owner-bound vs org-owned devices
- transfers need their own audit trail
- consent needs to stay attached to the active ownership binding

## Roles

The RBAC model used by the backend includes:

- `owner`
- `admin`
- `org_admin`
- `super_admin`
- `security_operator`
- `security`

For this workflow, the important rule is:

- only owner/admin-style roles can perform a locate request
- security operators may help with review workflows, but they do not get locate power by default

That rule is enforced in the backend, not by trusting what the phone UI says.

## Pairing and Ownership Proof

Important backend files:

- [`ownership.py`](../backend/app/api/v1/endpoints/ownership.py)
- [`ownership_access_service.py`](../backend/app/services/ownership_access_service.py)
- [`models.py`](../backend/app/db/models.py)

Pairing proof is modeled explicitly with `OwnershipProofKind` values such as:

- `ENROLLMENT_TOKEN`
- `QR_CODE`
- `ADMIN_APPROVAL`
- `TRANSFER_APPROVAL`
- `MANUAL_REVIEW`

This is better than a free-form string because:

- code can enforce expected cases
- audits are easier to filter
- the student reading the code can understand what kind of proof exists

## Key Registration and Device Identity

During pairing, Android generates or loads a device keypair and sends the public key to the backend.

Why:

- the backend needs a stable device identity that is safer than IMEI/IMSI/serial
- later telemetry can reference the registered key ID
- the private key stays on the phone

Current state:

- the Android side uses Android Keystore-backed key generation
- the backend stores the public key as a `DeviceKey`
- a verification endpoint checks whether the device, active enrollment, and active key still line up

Important limitation:

- this is registration and identity wiring, not full proof-of-possession cryptography yet
- signed telemetry is still a placeholder design and should be hardened later

## Per-Device Access Policy

Each device can have an access policy record.

That policy controls questions such as:

- can the owner locate the device?
- can admins locate the device?
- can a security operator review the case?
- does the device require an access review before broader access is granted?

This is stored in `device_access_policies`.

That is more flexible than hardcoding every rule directly into role checks.

## Locate Requests

Every locate request is audited, even when it is denied.

That is important because denied access attempts are often just as useful as successful ones during an investigation.

The locate flow is:

```text
Caller sends locate request
  -> JWT identity resolved
  -> role check passes route gate
  -> tenant/org check passes
  -> active ownership binding loaded
  -> per-device access policy loaded
  -> authorize_locate() decides allow/deny
  -> audit log entry written
  -> if allowed, latest location is returned
```

Important consequence:

- the platform does not quietly answer location lookups without leaving a trail

## Ownership Transfer

Ownership transfer is modeled as a workflow instead of directly editing a device row.

Why:

- transfers are sensitive
- there should be a reason and a decision point
- the old ownership binding should be ended, not silently overwritten

The flow is:

```text
transfer request created
  -> admin decision recorded
  -> old binding ended
  -> new binding created
  -> audit event appended
```

## Access Reviews

Access review is for situations where administrators want explicit review and decision history around a device.

The backend now supports:

- creating access reviews
- listing access reviews
- approving/rejecting access reviews

When a review is pending or rejected, the device access policy can be tightened.

## API Endpoints

Implemented endpoints under `/api/v1/ownership`:

- `POST /pairing-tokens`
- `POST /pairings/complete`
- `GET /devices/{device_id}/binding`
- `GET /devices/{device_id}/access-policy`
- `PUT /devices/{device_id}/access-policy`
- `POST /devices/{device_id}/transfers`
- `POST /transfers/{transfer_id}/decision`
- `POST /devices/{device_id}/access-reviews`
- `GET /access-reviews`
- `POST /access-reviews/{access_review_id}/decision`
- `POST /enrollments/{enrollment_id}/revoke`
- `POST /devices/{device_id}/locate`
- `POST /device-identity/verify`

## Database Tables Added

The main ownership/RBAC tables are:

- `device_ownership_bindings`
- `device_access_policies`
- `pairing_tokens`
- `ownership_transfers`
- `access_reviews`

These tables extend the earlier tenant/device/enrollment/audit foundation instead of replacing it.

## Tests

Focused tests for this feature live in:

- [`test_ownership_access_control.py`](../backend/tests/test_ownership_access_control.py)
- [`EnrollmentRepositoryImplTest.kt`](../app/src/test/java/com/example/trackme/data/repository/EnrollmentRepositoryImplTest.kt)
- [`EnrollmentViewModelTest.kt`](../app/src/test/java/com/example/trackme/feature/enrollment/EnrollmentViewModelTest.kt)

These tests cover:

- owner locate authorization
- security operator locate denial
- locate request auditing
- backend pairing success and offline fallback behavior
- Android form validation and scheduling behavior
