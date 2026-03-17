# Event Queue And Rules Engine

This layer gives the backend an asynchronous path for recovery signals that should not be handled inline with the original API request.

## Why This Exists

Some decisions need to happen after an event is stored:

- a geofence exit may need escalation only if an incident is active
- a device may become stale only after enough time has passed with no new check-in
- repeated locate requests may look normal once, but suspicious after a pattern builds up
- pending commands may need delayed retry or expiry

That is what the event queue and consumer workers handle.

## Queue Design

The current implementation uses a simple internal queue abstraction with a SQL-backed default implementation.

Important files:

- [`backend/app/schemas/events.py`](../backend/app/schemas/events.py)
- [`backend/app/services/event_queue_service.py`](../backend/app/services/event_queue_service.py)
- [`backend/app/db/models.py`](../backend/app/db/models.py)
- [`backend/alembic/versions/20260317_0008_event_queue_rules.py`](../backend/alembic/versions/20260317_0008_event_queue_rules.py)

### Why SQL-backed first

This project already depends on PostgreSQL and needs strict auditability. A database-backed queue gives us:

- durable event persistence
- idempotency by unique `idempotency_key`
- retry metadata
- replay-safe handoff with `PENDING -> PROCESSING -> COMPLETED/FAILED`

The abstraction leaves room for a future Redis Streams or Kafka adapter.

## Event Topics

Current topics:

- `location.updated`
- `geofence.transition`
- `incident.state_changed`
- `command.acknowledged`
- `suspicious_access.alert`
- `incident.offline_check`
- `command.pending_check`

The last two are delayed follow-up checks. They are important because “offline too long” and “pending too long” are time-based rules, not immediate request-time rules.

## Consumers

Important file:

- [`backend/app/services/event_consumer_worker.py`](../backend/app/services/event_consumer_worker.py)

Consumer responsibilities:

- `LocationUpdateConsumer`
  Schedules delayed offline checks for active incidents.
- `GeofenceEventConsumer`
  Enriches the event with active incident context and evaluates rules.
- `IncidentStateChangeConsumer`
  Schedules delayed offline checks when an incident becomes active.
- `CommandAcknowledgementConsumer`
  Reserved hook for command lifecycle reactions.
- `SuspiciousAccessAlertConsumer`
  Enriches suspicious-access signals with recent audit counts.
- `IncidentOfflineCheckConsumer`
  Evaluates whether the device should be treated as stale.
- `CommandPendingCheckConsumer`
  Retries or expires commands when they remain pending too long.

## Rules, Triggers, Actions

Important files:

- [`backend/app/services/rules_engine_service.py`](../backend/app/services/rules_engine_service.py)
- [`backend/app/services/rule_action_executor.py`](../backend/app/services/rule_action_executor.py)

The separation is:

- `triggers`
  Topic-specific events, optionally enriched by a consumer with database context.
- `rules`
  Pure evaluation of the enriched event into rule matches.
- `actions`
  Executed later by the action executor.

That keeps rule logic easier to test and avoids mixing database lookups with notification/audit side effects.

## Implemented Rules

### 1. Geofence exit during lost mode

If:

- a `geofence.transition` event is an `exit`
- the event was not rate-limited by geofence processing
- the device still has an active incident with `lost_mode_until` in the future

Then:

- create an internal escalation notification
- append an immutable audit record

### 2. Device offline too long during active incident

If:

- an `incident.offline_check` fires
- the incident is still active
- the latest location is still older than the threshold
- no newer location arrived since the check was scheduled

Then:

- create an internal stale-device notification
- append an immutable audit record

### 3. Repeated locate requests from unusual admin activity

If:

- a `suspicious_access.alert` signal is enriched with high lookup counts
- the recent pattern crosses the configured threshold

Then:

- create an internal abuse alert
- append an immutable audit record

### 4. Command pending too long

If:

- a delayed `command.pending_check` finds the action still pending and valid

Then:

- retry delivery

If:

- the command has expired or crossed the max-attempt limit

Then:

- expire it
- append an immutable audit record

## Rate Limiting

Rule actions that would otherwise spam operators use a cooldown lock table:

- [`RuleExecutionLock`](../backend/app/db/models.py)

This prevents the same rule from re-emitting the same alert scope repeatedly during the cooldown window.

## Auditability

The queue itself stores:

- producer
- topic
- entity type/id
- idempotency key
- attempts
- errors
- completion timestamps

On top of that, rule actions append immutable audit-log entries for escalations, stale-device marking, unusual locate activity, and command expiry/retry paths.

## Tests

Important file:

- [`backend/tests/test_event_queue_and_rules.py`](../backend/tests/test_event_queue_and_rules.py)

Current tests cover:

- queue idempotency
- replay-safe completion
- rule matching for all required rule families
- cooldown/rate limiting for repeated alerts
- consumer worker dispatch
