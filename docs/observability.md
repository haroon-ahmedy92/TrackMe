# Observability And Abuse Resistance

This platform uses privacy-preserving observability. We measure service health and misuse patterns without turning the platform into a surveillance system.

## Structured Audit Schema

Every immutable backend audit event includes:

- `actor_sub`
- `action`
- `entity_type`
- `entity_id`
- `occurred_at`
- `previous_hash`
- `event_hash`
- `metadata`

Structured metadata defaults:

- `schema_version`
- `privacy_preserving`
- `recorded_at`
- request-specific fields such as `reason`, `result`, `device_id`, and `request_id`

Locate requests are explicitly audited with:

- actor
- reason
- timestamp
- target device
- authorization result
- locate result

## Dashboard Panels

The backend exposes dashboard-ready summaries for:

1. Ingestion health
   - number of location events
   - last ingestion timestamp
   - approximate-source count
   - verified telemetry count
2. Failed commands
   - failed and expired command counts
   - top command error reasons
3. Battery impact
   - average reported battery
   - low-battery event count
4. Location confidence distribution
   - high / medium / low confidence buckets
   - precise / moderate / approximate distribution
5. Suspicious actor behavior
   - highest-volume lookup actor
   - denied lookup counts
   - unique lookup actor count

## Alert Rules

Current anomaly rules:

1. `bulk_location_lookup`
   - triggered when one actor performs unusually high volumes of locate requests
2. `repeated_locate_denied`
   - triggered when one actor has repeated denied locate attempts
3. `repeated_failed_authorization`
   - triggered when HTTP 401/403 failures spike in the current window
4. `command_failure_spike`
   - triggered when failed or expired remote commands exceed threshold

## OpenTelemetry Hooks

The backend includes lightweight OpenTelemetry hooks:

- request middleware creates an `http.request` span when OpenTelemetry is installed
- if OpenTelemetry is not installed, the same code path safely degrades to no-op spans

The Android app records structured local audit metadata so future OTLP export can map cleanly to:

- check-in events
- remote command execution
- local failure paths

## Privacy Defaults

- approximate location remains explicitly labeled approximate
- observability reports are organization-scoped
- auth-failure tracking stores only minimal request context
- audit exports are JSON reports, not raw database dumps
- no hidden or covert collection is added by observability features
