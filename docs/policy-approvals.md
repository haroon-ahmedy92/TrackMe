# Authorization Policy Engine And Approval Workflows

This document explains the new backend authorization layer for sensitive actions.

## What it covers

- policy checks for `locate`, `lock`, `wipe`, and `evidence_export`
- tenant-level access rules
- per-device access policy overrides
- approval workflows for high-risk actions
- explainable allow or deny reasons
- immutable audit linkage for policy decisions

## Core idea

Before a sensitive action runs, the backend now answers two questions:

1. `Is this action allowed at all?`
2. `If it is allowed, does it need approval before execution?`

That decision is made by `AuthorizationPolicyService` in:

- [`backend/app/services/authorization_policy_service.py`](../backend/app/services/authorization_policy_service.py)

The decision is returned as a structured `PolicyDecision` with:

- action type
- allowed or denied
- whether approval is required
- how many approvals are required
- an explainable reason code
- a user-facing reason message

## What inputs the policy engine uses

The policy engine evaluates actions using:

- caller role
- bound owner identity when relevant
- active incident state
- reason text quality
- tenant settings
- per-device access policy
- device management state

This means the system does not rely on role checks alone. A valid role still is not enough if:

- the device policy disables that action
- the incident is in the wrong state
- the reason text is too weak
- the tenant requires an active incident or extra approval

## Tenant rules

Tenant-wide rules are stored in `tenant_settings`.

New fields:

- `locate_reason_min_length`
- `require_incident_for_locate`
- `lock_requires_active_incident`
- `wipe_requires_policy_approval`
- `wipe_requires_confirmed_stolen`
- `high_risk_actions_require_two_person`
- `evidence_export_requires_permission`

These are returned through the platform settings API and can be updated only by admin-level roles.

## Device-level overrides

Per-device policy is stored in `device_access_policies`.

New fields:

- `owner_can_export_evidence`
- `admin_can_export_evidence`
- `security_can_export_evidence`
- `admin_can_lock`
- `admin_can_wipe`
- `require_incident_for_locate`
- `require_two_person_wipe_approval`

This gives the platform a clean separation:

- tenant settings decide organization-wide defaults
- device access policy handles exceptions or stricter controls for a specific asset

## Approval workflow

Approval records are stored separately from the sensitive entity itself.

Tables:

- `sensitive_action_approvals`
- `sensitive_action_approval_decisions`

This lets us support:

- one-person approval
- optional two-person approval
- distinct approver tracking
- rejection with reason
- auditable approval history

Approval logic lives in:

- [`backend/app/services/approval_workflow_service.py`](../backend/app/services/approval_workflow_service.py)

Important behavior:

- the requester cannot approve their own request
- the same person cannot approve twice
- once the required number of approvals is reached, the request becomes `approved`
- a rejection closes the request immediately

## How actions behave now

### Locate

Handled in:

- [`backend/app/api/v1/endpoints/ownership.py`](../backend/app/api/v1/endpoints/ownership.py)

Rules include:

- owner or admin role required
- valid purpose required
- owner must match the active owner binding
- tenant or device can require an active incident

Every locate request logs:

- actor
- device
- reason text
- decision code
- decision message
- final result

### Lock

Handled in:

- [`backend/app/api/v1/endpoints/platform.py`](../backend/app/api/v1/endpoints/platform.py)

Rules include:

- authorized admin/security role
- policy-managed device
- valid reason text
- tenant can require an active incident

### Wipe

Handled in:

- [`backend/app/api/v1/endpoints/platform.py`](../backend/app/api/v1/endpoints/platform.py)

Rules include:

- admin-level role only
- policy-managed device
- elevated confirmation required
- tradeoff acknowledgement required
- tenant can require `CONFIRMED_STOLEN`
- tenant or device can require one or two approvers

If approval is required:

- the `remote_action` is created in `pending_approval`
- a matching approval record is created
- dispatch must wait until approval completes

### Evidence export

Handled in:

- [`backend/app/api/v1/endpoints/platform.py`](../backend/app/api/v1/endpoints/platform.py)

Rules include:

- permission-gated by role and device policy
- valid reason text required
- tenant rules can block export for irrelevant incident states

If approval is required in the future, the same approval workflow already supports it. The current structure is designed so that export records can stay in `pending_approval` until released.

## New APIs

- `GET /api/v1/platform/remote-actions`
- `GET /api/v1/platform/approvals`
- `POST /api/v1/platform/approvals/{approval_id}/decision`
- `POST /api/v1/platform/remote-actions/{action_id}/approve`
- `POST /api/v1/platform/remote-actions/{action_id}/reject`

Existing APIs now include policy behavior:

- `POST /api/v1/ownership/devices/{device_id}/locate`
- `POST /api/v1/platform/remote-actions`
- `POST /api/v1/platform/cases/{incident_id}/exports`
- `PUT /api/v1/platform/settings/retention-policy`

## Audit linkage

Policy decisions are written into immutable audit logs with:

- allow or deny result
- reason code
- reason text
- target entity
- actor
- request reason

This is important because approvals alone are not enough. We also need to know why the system allowed or blocked the action.

## UI hooks

The admin console now has hook points for:

- showing approval counts on remote actions
- showing policy reason text on remote actions
- showing evidence export requests that are still waiting for approval
- displaying the new tenant policy fields in the settings payload

These UI updates are intentionally light. The main goal of this pass was to make the backend rules real and explainable first.
