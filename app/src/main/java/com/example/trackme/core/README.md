# Core Package

Shared, framework-agnostic helpers:
- `TimeProvider`: testable time source.
- `Hasher`: SHA-256 support used for tamper-evident audit chaining.
- `TelemetrySigner`: canonical payload hashing + Android Keystore-backed device signing.

Keep this package small and dependency-light.
