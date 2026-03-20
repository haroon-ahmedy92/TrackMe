# Operator Support And Evidence Exports

This feature set helps admins and operators work a recovery case without mixing editable working notes with immutable evidence.

## What Was Added

- A support dashboard in the admin console at `/support`
- Incident filtering by:
  - state
  - update date range
  - tenant
  - assigned operator
  - free-text search
- Incident assignment with reason logging
- Evidence export packages for an incident
- External sharing with required reason text
- CSV-first export bundles, JSON bundles, and PDF placeholder summaries

## Why This Matters

Recovery work usually has two kinds of records:

1. Mutable working notes
   - operators update these while investigating
   - they are useful, but they are not the same thing as immutable evidence

2. Immutable evidence and audit records
   - location samples
   - geofence alerts
   - command attempts
   - actor/action audit trail
   - export/share records

The code keeps those separate on purpose.

## Backend Design

Main files:

- [`backend/app/services/case_evidence_service.py`](../backend/app/services/case_evidence_service.py)
- [`backend/app/services/evidence_export_bundle_service.py`](../backend/app/services/evidence_export_bundle_service.py)
- [`backend/app/services/case_management_service.py`](../backend/app/services/case_management_service.py)
- [`backend/app/api/v1/endpoints/platform.py`](../backend/app/api/v1/endpoints/platform.py)

### `CaseEvidenceService`

This service prepares the case record in structured sections:

- `incident_summary`
- `location_timeline`
- `audit_trail`
- `command_history`
- `geofence_events`
- `notes`
- `attachments`
- `exports`
- `external_shares`
- `entries`

`entries` is the unified timeline view.

The separate sections are for exports, operator review, and clearer UI rendering.

### `EvidenceExportBundleService`

This service writes export bundles to disk.

Supported formats:

- `csv`
  - writes multiple CSV files into one zip bundle
  - best first choice for operations and data review
- `json`
  - writes one structured JSON evidence summary
- `pdf`
  - placeholder summary for human-readable handoff

CSV bundles currently include:

- `incident-summary.csv`
- `location-timeline.csv`
- `actor-action-audit-trail.csv`
- `command-history.csv`
- `geofence-events.csv`
- `notes.csv`
- `attachments.csv`
- `external-shares.csv`
- `manifest.json`

### Approximate Location Labeling

Approximate points are never exported as if they were exact.

The location timeline includes fields like:

- `precision`
- `source_label`
- `approximate_label`

If a point came from an approximate source such as backend IP geolocation, the export marks it clearly.

## API Endpoints

Relevant endpoints:

- `GET /api/v1/platform/incidents`
- `POST /api/v1/platform/cases/{incident_id}/assign`
- `GET /api/v1/platform/cases/{incident_id}/evidence-chain`
- `POST /api/v1/platform/cases/{incident_id}/exports`
- `GET /api/v1/platform/cases/{incident_id}/exports/{export_id}/download`
- `POST /api/v1/platform/cases/{incident_id}/exports/{export_id}/share`

### Filters

`GET /platform/incidents` supports:

- `org_id`
- `incident_state`
- `updated_from`
- `updated_to`
- `assigned_operator_sub`
- `search`

## Audit Expectations

Every important action is logged:

- incident assignment
- export creation
- export download
- external share attempts
- policy allow/deny decisions for export/share

This keeps exports auditable even when notes remain editable.

## Admin Console

Main files:

- [`admin-console/src/app/(dashboard)/support/page.tsx`](../admin-console/src/app/(dashboard)/support/page.tsx)
- [`admin-console/src/app/(dashboard)/incidents/page.tsx`](../admin-console/src/app/(dashboard)/incidents/page.tsx)
- [`admin-console/src/lib/api/restApi.ts`](../admin-console/src/lib/api/restApi.ts)
- [`admin-console/src/lib/mocks/mockApi.ts`](../admin-console/src/lib/mocks/mockApi.ts)

### Support Dashboard

The support dashboard is the queue view.

It helps an operator:

- filter cases
- select a case
- assign an operator
- jump into the full incident workspace

### Incident Workspace

The incident page is the deep-dive view.

It supports:

- route and location evidence review
- notes
- attachment metadata
- export requests
- external sharing
- evidence-chain review

## Migration

This feature adds:

- `csv` as an `evidenceexportformat`
- `assigned_operator_sub` on `incidents`

Migration file:

- [`backend/alembic/versions/20260320_0012_operator_support_exports.py`](../backend/alembic/versions/20260320_0012_operator_support_exports.py)

Run:

```bash
cd backend
alembic upgrade head
```

## Tests

Primary test file:

- [`backend/tests/test_case_evidence_endpoints.py`](../backend/tests/test_case_evidence_endpoints.py)

This covers:

- redaction behavior
- case evidence chain response
- export creation
- export download
- external share logging
- CSV bundle generation
