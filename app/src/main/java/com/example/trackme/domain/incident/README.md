# Incident Domain Package

This package contains lawful incident lifecycle logic for device recovery workflows.

Key rules:
- Explicit incident states only: `NORMAL`, `SUSPECTED_LOST`, `CONFIRMED_STOLEN`, `RECOVERED`, `WIPED`, `DECOMMISSIONED`.
- `CONFIRMED_STOLEN` requires elevated confirmation.
- Remote wipe is only valid after confirmed stolen and must include tradeoff acknowledgement.
- All sensitive actions are expected to emit immutable audit events.

Files:
- `IncidentStateMachine.kt`: transition rules and lock/wipe eligibility checks.
- `IncidentAuditEvents.kt`: shared audit event type constants.
