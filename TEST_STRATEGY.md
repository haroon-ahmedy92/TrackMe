# TrackMe Test Strategy

This document defines the test strategy for the TrackMe Android app, FastAPI backend, and web-facing operational behavior of the lawful device recovery platform.

The goal is not only correctness. The test plan is also designed to prevent misuse, false confidence, broken tenant boundaries, and silent policy regressions.

## Test Principles

- Treat consent, visibility, and auditability as testable product requirements.
- Prefer deterministic unit tests for domain logic and security rules.
- Use integration tests for storage, API authorization, and workflow coordination.
- Simulate unreliable network and battery-sensitive conditions explicitly.
- Never treat approximate signals as precise in tests, UI expectations, or API contracts.

## Current Baseline

### Android tests already present

- `LocationConfidenceScorerTest`
- `LocationSpoofingDetectorTest`
- `IncidentStateMachineTest`
- `RequestRemoteActionUseCaseTest`

### Backend tests already present

- `test_health.py`
- `test_incident_state_machine.py`
- `test_location_confidence.py`
- `test_integrity_and_telemetry_security.py`

## Test Matrix

| Area | Scope | Test Type | Priority | Primary Goal |
|---|---|---|---|---|
| Android domain models/use cases | incident, consent, check-in, remote actions | unit | critical | Prevent unlawful or invalid state transitions |
| Android ViewModels | onboarding, enrollment, incidents, settings, map | unit | high | Validate UI state, errors, and permission handling |
| Android repositories | Room + preferences + network mapping | unit/integration | high | Validate data mapping, consent state, audit appends |
| Android WorkManager | normal mode, lost mode, delayed wipe | unit/integration | critical | Ensure no silent scheduling without consent |
| Android location engine | confidence, spoof detection, stale data, approximate-only | unit | critical | Prevent false precision and bad evidence |
| Backend service layer | incident workflow, key rotation, telemetry verification | unit | critical | Enforce business and security invariants |
| Backend API layer | auth, RBAC, tenant isolation, BOLA | integration | critical | Prevent cross-tenant access and insider overreach |
| Database migrations | Alembic + PostGIS schema evolution | integration | high | Ensure upgrades are repeatable and safe |
| Geofence rules | create/evaluate/transition logic | unit/integration | high | Prevent noisy or missing protection alerts |
| Offline/poor network | Android sync + retry behavior | integration/manual | high | Avoid data loss and misleading freshness |
| Performance and battery | check-in cadence, lost mode window, background work | manual/benchmark | medium | Keep lawful tracking battery-aware |
| False precision prevention | UI, API, storage, audit labels | unit/integration/manual | critical | Ensure approximate never appears exact |

## Android Strategy

### 1. Unit tests

Focus on pure logic and rule enforcement.

Required coverage:

- `PerformCheckInUseCase`
  - skips when not enrolled
  - skips when explicit tracking consent is not granted
  - skips active location capture in normal mode on low battery
  - records audit metadata with approximate vs precise labeling
- `SetLostModeUseCase`
  - enables lost mode state
  - does not schedule lost mode work without consent
  - appends audit event on enable/disable
- `EnrollDeviceUseCase`
  - stores explicit consent state
  - records enrollment audit event
- `ManageIncidentLifecycleUseCase`
  - mark lost
  - confirm stolen with elevated confirmation phrase
  - reject wipe without tradeoff acknowledgement
  - recover after theft report
- `LocationFusionEngine` collaborators
  - stale last known location lowers confidence
  - approximate IP-only result remains approximate
  - suspected mock location adds spoofing reasons

### 2. ViewModel tests

Test with fake repositories and `runTest`.

ViewModels to cover:

- `OnboardingViewModel`
  - consent checkbox state
  - permission refresh
  - skip background permission path
- `EnrollmentViewModel`
  - blank organization rejected
  - authorization confirmation required
  - success navigates only after enrollment and scheduling
- `IncidentsViewModel`
  - lost/stolen/recovery flows expose success and error states
- `SettingsPrivacyViewModel`
  - geofence toggle/radius update messages
- `HomeViewModel` and `MapViewModel`
  - approximate location presented with correct labels

### 3. Repository tests

Use in-memory Room and fake network services.

Targets:

- `AuditRepositoryImpl`
  - hash chain continuity
  - metadata serialization stability
- `EnrollmentRepositoryImpl`
  - enrollment state persisted and observed
- `LocationRepositoryImpl`
  - DB mapping preserves `isApproximate`, `confidenceScore`, `suspiciousMockLocation`
- `DeviceStateRepositoryImpl`
  - lost mode state survives updates
- `TrackingPreferencesDataSource`
  - explicit consent grant/revoke
  - geofence and interval persistence

### 4. WorkManager tests

Add:

- `androidx.work:work-testing`
- `kotlinx-coroutines-test`

Scenarios:

- normal work scheduled only when enrolled and explicit consent is granted
- lost mode work cancelled when window expires
- lost mode work not scheduled without explicit consent
- delayed wipe worker triggers due execution path only after scheduled time
- network/battery constraints applied correctly

### 5. Android edge-case cases

Required cases:

- permission denied
- location disabled
- device offline
- stale last known location
- approximate IP-only result
- suspected mock location
- remote lock requested while offline
- wipe approval flow
- recovery after theft report

## Backend Strategy

### 1. Unit tests

Targets:

- `SignedTelemetryService`
  - missing signature/key/hash rejected
  - bad hash format rejected
  - signature mismatch rejected
  - known active key accepted only when digest matches
- `IntegrityVerificationService`
  - trusted placeholder verdicts
  - unavailable verdicts
  - untrusted verdicts
- `DeviceKeyService`
  - register key
  - rotation deactivates previous active keys
  - invalid PEM rejected
- `LocationIngestionService`
  - suspicious alerts emitted for low-confidence, stale, untrusted integrity, digest mismatch
  - duplicate idempotency returns duplicate result
- `CaseManagementService` and `IncidentService`
  - cross-tenant access rejected
  - wipe requires elevated confirmation
  - delayed wipe preserved

### 2. API integration tests

Use FastAPI test app with async client and seeded tenant data.

Must cover:

- JWT missing -> `401`
- insufficient role -> `403`
- foreign tenant `device_id` -> `403`
- foreign tenant `incident_id` -> `403`
- audit endpoint returns only caller tenant records
- remote action endpoints reject unmanaged devices
- `/platform/audit-logs/verify` returns valid chain state
- approximate-only ingestion returns `ip_is_approximate=true` and suspicious alert if applicable

### 3. Database migration tests

Test strategy:

- create empty test database
- run `alembic upgrade head`
- verify tables, indexes, PostGIS extension
- insert representative row set
- run downgrade/upgrade cycle where supported
- verify new columns like telemetry digest fields and audit chain fields remain consistent

Checks:

- `location_events` unique `(device_id, idempotency_key)`
- GIST indexes exist for geospatial fields
- audit tables still query by `org_id + occurred_at`

### 4. Security and authorization tests

Mandatory categories:

- broken object-level authorization
- role escalation attempts
- token verification disabled in non-dev environments
- audit log chain verification with tampered row
- stale telemetry replay attempt
- insider abuse:
  - org admin tries cross-tenant device access
  - security role tries org creation if not allowed
  - owner role tries remote wipe

## Geofence Rule Tests

Coverage:

- geofence creation with valid radius and tenant-owned device
- reject foreign-tenant device geofence
- enabled geofence only
- entry/exit transitions produce expected rule matches
- no alert when device remains inside zone
- stale location sample does not trigger fresh geofence breach alert

## Poor Network and Offline Sync Strategy

### Android behavior to test

- check-in capture with no network should still update local audit and local last-known state
- retries should not duplicate backend events once connectivity returns
- idempotency key remains stable across retry path
- old approximate fallback data must not overwrite fresher precise local sample as if it were better

### Poor network simulation

Use:

- Android emulator network throttling
- `adb shell cmd network` or emulator extended controls
- backend proxy delay/failure injection
- 2G/EDGE simulation
- packet loss and intermittent disconnect windows

### Offline-to-online sync checks

- enqueue local check-in while offline
- restore network
- verify one backend ingest event only
- verify audit sequence: captured offline -> queued -> sent -> acknowledged
- verify UI freshness timestamps do not claim live precision during offline period

## False Precision Prevention Checks

These are mandatory because false precision is a safety and misuse problem.

Validate:

- approximate IP-only result is labeled `approximate`
- no map pin language implies exact live location
- API response includes `ip_is_approximate`
- audit events preserve approximate flag
- ViewModels do not collapse approximate and moderate into one generic “located” state
- stale last known location never renders as “live”

## Example Test Code

### Android unit test example

```kotlin
@Test
fun `perform check-in skips when explicit consent is missing`() = runTest {
    val auditRepo = FakeAuditRepository()
    val useCase = PerformCheckInUseCase(
        enrollmentRepository = FakeEnrollmentRepository(enrolled = true),
        trackingPreferences = FakeTrackingPreferences(consentGranted = false),
        deviceStateRepository = FakeDeviceStateRepository(),
        locationRepository = FakeLocationRepository(),
        integrityRepository = FakeIntegrityRepository(),
        auditRepository = auditRepo,
        telemetrySigner = FakeTelemetrySigner(),
        timeProvider = FakeTimeProvider(now = 1_700_000_000_000),
        batteryManager = FakeBatteryManager(80),
        json = Json
    )

    useCase(CheckInMode.NORMAL, "test")

    assertThat(auditRepo.events.single().type).isEqualTo("CHECKIN_SKIPPED")
    assertThat(auditRepo.events.single().summary).contains("explicit tracking consent")
}
```

### Android ViewModel test example

```kotlin
@Test
fun `enrollment view model requires organization and authorization`() = runTest {
    val viewModel = EnrollmentViewModel(
        enrollDeviceUseCase = FakeEnrollDeviceUseCase(),
        getEnrollmentDisclosureUseCase = FakeDisclosureUseCase(),
        checkInScheduler = FakeCheckInScheduler()
    )

    viewModel.onOrganizationNameChanged("")
    viewModel.onAuthorizationConfirmed(false)
    viewModel.enroll {}

    val state = (viewModel.uiState.value as AsyncUiState.Data).value
    assertThat(state.errorMessage).isNotNull()
}
```

### WorkManager test example

```kotlin
@Test
fun `lost mode worker disables lost mode when window expired`() = runTest {
    val worker = buildLostModeWorker(untilEpochMs = 1000L, nowEpochMs = 2000L)

    val result = worker.doWork()

    assertThat(result).isEqualTo(ListenableWorker.Result.success())
    assertThat(fakeSetLostModeUseCase.disableCalled).isTrue()
}
```

### Backend authorization test example

```python
@pytest.mark.asyncio
async def test_platform_case_confirm_stolen_rejects_foreign_tenant(async_client, foreign_incident_id, owner_token):
    response = await async_client.post(
        f"/api/v1/platform/cases/{foreign_incident_id}/confirm-stolen",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"reason": "attempted cross-tenant access", "elevated_confirmation": True},
    )

    assert response.status_code == 403
```

### Backend migration test example

```python
def test_alembic_upgrade_creates_postgis_tables(alembic_runner, inspector):
    alembic_runner.upgrade("head")
    tables = set(inspector.get_table_names())
    assert "location_events" in tables
    assert "audit_logs" in tables
    assert "device_keys" in tables
```

## CI Recommendations

### Required CI jobs

1. Android unit tests
   - `./gradlew testDebugUnitTest`
2. Backend tests
   - `PYTHONPATH=backend pytest -q backend/tests`
3. Backend import/compile smoke
   - `python -m compileall -q backend/app`
4. Admin console quality
   - `npm install`
   - `npm run lint`
   - `npm run typecheck`
5. Migration verification
   - spin up PostgreSQL + PostGIS service
   - run `alembic upgrade head`
   - run migration tests

### Recommended CI stages

- `fast`
  - Android unit tests
  - backend unit tests
  - frontend lint/typecheck
- `security`
  - authz/BOLA integration tests
  - telemetry verification tests
  - audit-chain verification tests
- `database`
  - alembic upgrade tests
  - PostGIS availability checks
- `nightly`
  - emulator-based WorkManager and offline/network tests
  - performance and battery regression sampling

### Tooling additions recommended

- Android:
  - `kotlinx-coroutines-test`
  - `androidx.arch.core:core-testing`
  - `androidx.work:work-testing`
  - `app.cash.turbine`
  - `mockk` or fake-based test fixtures
- Backend:
  - `pytest-cov`
  - async HTTP client fixture
  - disposable PostgreSQL/PostGIS test container

## Manual QA Checklist

### Consent and permissions

- App icon is visible in launcher.
- Onboarding disclosure is shown before enrollment.
- Enrollment cannot finish without explicit authorization confirmation.
- Deny foreground location and confirm the app does not behave as if protected tracking is active.
- Deny background location and confirm normal app usage remains available without covert fallback.

### Location behavior

- Disable device location and confirm UI explains no fresh precise location is available.
- Force approximate-only input and confirm UI labels it approximate.
- Use stale last known location and confirm it is not shown as live.
- Simulate mock location and confirm suspicious indicator/audit record appears.

### Incident and remote action behavior

- Mark device as lost and confirm visible lost-mode behavior.
- Request remote lock while device is offline and confirm request is queued/audited, not falsely marked executed.
- Exercise wipe approval flow and confirm elevated confirmation and tradeoff acknowledgement are required.
- Recover device after theft report and confirm lost mode ends and audit history is intact.

### Network resilience

- Capture state while offline, then reconnect and confirm one ingest event reaches backend.
- Simulate intermittent connection and confirm retries do not create duplicate telemetry.
- Validate low-bandwidth mode still updates last check-in timestamps without UI freezes.

### Security and authz

- Use a lower-privilege account and verify remote wipe is blocked.
- Use a tenant A account with tenant B IDs and verify access is denied.
- Tamper with audit row in test environment and confirm audit-chain verification detects breakage.

## Exit Criteria

TrackMe should not be considered test-complete until all of the following are true:

- critical incident, consent, and authz paths have automated tests
- approximate-vs-precise labeling is covered in unit and manual tests
- offline retry and idempotency behavior is proven
- cross-tenant object access tests pass
- remote wipe decision flow is fully covered
- audit chain verification passes and tamper detection is tested
