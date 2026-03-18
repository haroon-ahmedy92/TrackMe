# Device Identity And Signed Telemetry

This document explains how TrackMe now handles device identity, key registration, signed telemetry, and key revocation.

## Why This Exists

A recovery backend should not trust a device just because it sent JSON with a `device_id`.

That is why TrackMe now uses a stronger identity path:

- the Android app generates a signing key during enrollment
- the private key stays in Android Keystore
- the backend stores the device public key
- telemetry includes a payload hash, key ID, algorithm, and signature
- the backend recomputes the payload hash and verifies the signature

## Android Flow

Important files:

- [`app/src/main/java/com/example/trackme/core/security/DeviceKeyMaterialGenerator.kt`](../app/src/main/java/com/example/trackme/core/security/DeviceKeyMaterialGenerator.kt)
- [`app/src/main/java/com/example/trackme/core/TelemetrySigner.kt`](../app/src/main/java/com/example/trackme/core/TelemetrySigner.kt)
- [`app/src/main/java/com/example/trackme/data/repository/EnrollmentRepositoryImpl.kt`](../app/src/main/java/com/example/trackme/data/repository/EnrollmentRepositoryImpl.kt)
- [`app/src/main/java/com/example/trackme/domain/usecase/PerformCheckInUseCase.kt`](../app/src/main/java/com/example/trackme/domain/usecase/PerformCheckInUseCase.kt)
- [`app/src/main/java/com/example/trackme/data/repository/CommandRepositoryImpl.kt`](../app/src/main/java/com/example/trackme/data/repository/CommandRepositoryImpl.kt)

### Enrollment

During enrollment:

1. the app generates or loads a device signing key from Android Keystore
2. the app sends the public key, key ID, signature algorithm, and attestation placeholders to the backend pairing endpoint
3. the backend stores that public key in `device_keys`

### Signing model

The app signs a canonical payload hash, not the raw request body bytes.

That is important because:

- request field order can vary between client and server
- a canonical hash is easier to recompute safely on the backend
- the same pattern works for location ingest, check-ins, and command acknowledgements

### Current Android algorithms

For new keys, Android currently prefers:

- `SHA256withECDSA`

The code still understands RSA-backed keystore entries if an older key exists.

### Attestation placeholders

The app now captures placeholder attestation metadata when available:

- whether the key appears hardware-backed
- certificate-chain placeholder text
- attestation format label

This is stored so the real hardware-attestation path can be added later without redesigning the key model.

## Backend Flow

Important files:

- [`backend/app/services/signed_telemetry_service.py`](../backend/app/services/signed_telemetry_service.py)
- [`backend/app/services/device_key_service.py`](../backend/app/services/device_key_service.py)
- [`backend/app/services/location_ingestion_service.py`](../backend/app/services/location_ingestion_service.py)
- [`backend/app/services/telemetry_service.py`](../backend/app/services/telemetry_service.py)
- [`backend/app/api/v1/endpoints/commands.py`](../backend/app/api/v1/endpoints/commands.py)
- [`backend/app/api/v1/endpoints/platform.py`](../backend/app/api/v1/endpoints/platform.py)

### Verification steps

For a signed payload, the backend now:

1. checks whether all signature fields are present
2. recomputes the canonical payload hash from the parsed request body
3. compares that hash with the client-supplied payload hash
4. loads the registered device public key
5. rejects inactive or revoked keys
6. verifies the signature against the payload hash

If any signed payload is malformed or tampered, the backend rejects it.

## Dev Mode vs Production Mode

The setting is:

- `SIGNED_TELEMETRY_MODE=optional`
- or `SIGNED_TELEMETRY_MODE=required`

### Optional mode

Good for local development and migration.

Behavior:

- unsigned telemetry is accepted
- signed telemetry is still verified when provided
- malformed signed telemetry is rejected

### Required mode

Good for production.

Behavior:

- unsigned telemetry is rejected
- malformed signed telemetry is rejected
- revoked or inactive keys are rejected

There is also a temporary compatibility flag:

- `ALLOW_PLACEHOLDER_SIGNED_TELEMETRY`

That allows the older placeholder signature format during migration.

## Key Rotation And Revocation

TrackMe now supports:

- active key registration
- rotation of the active device key
- explicit key revocation
- audit records for registration, rotation, and revocation

Important API endpoints:

- `POST /api/v1/platform/device-keys`
- `POST /api/v1/platform/device-keys/rotate`
- `POST /api/v1/platform/device-keys/{key_record_id}/revoke`

Revoked keys remain in the database for audit history, but the backend will no longer accept signatures from them.

## Signed Payload Types

The system now supports signed fields for:

- location ingestion
- telemetry check-ins/status events
- command acknowledgements

## Database Changes

Important file:

- [`backend/alembic/versions/20260317_0009_device_identity_signed_telemetry.py`](../backend/alembic/versions/20260317_0009_device_identity_signed_telemetry.py)

New metadata includes:

- key hardware-backed flag
- attestation placeholders
- key revocation fields
- telemetry algorithm
- telemetry payload hash
- telemetry verification reason

## Tests

Important files:

- [`backend/tests/test_integrity_and_telemetry_security.py`](../backend/tests/test_integrity_and_telemetry_security.py)
- [`backend/tests/test_commands_endpoints.py`](../backend/tests/test_commands_endpoints.py)
- [`app/src/test/java/com/example/trackme/core/KeystoreTelemetrySignerTest.kt`](../app/src/test/java/com/example/trackme/core/KeystoreTelemetrySignerTest.kt)

These cover:

- valid asymmetric signature verification
- tampered signature rejection
- revoked key rejection
- optional unsigned mode behavior
- command-ack rejection on invalid signatures
- canonical payload hashing on Android
