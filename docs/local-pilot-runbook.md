# Local Pilot Runbook

Last updated: 2026-03-24

This runbook is the shortest path to starting the full TrackMe stack as one integrated pilot system.

## What you will run

1. FastAPI backend
2. PostgreSQL/PostGIS and Redis
3. Background worker for queue and rules processing
4. Next.js admin console
5. Android app pointed at the same backend

## 1. Generate command-signing keys

TrackMe now signs remote commands with an EC keypair instead of a placeholder shared secret.

```bash
cd /home/haroon/AndroidStudioProjects/TrackMe
mkdir -p backend/.secrets
openssl ecparam -name prime256v1 -genkey -noout -out backend/.secrets/command_signing_private.pem
openssl ec -in backend/.secrets/command_signing_private.pem -pubout -out backend/.secrets/command_signing_public.pem
```

## 2. Configure the backend

Copy the example file:

```bash
cd /home/haroon/AndroidStudioProjects/TrackMe/backend
cp .env.example .env
```

Important fields in `.env`:

- `JWT_SHARED_SECRET`
  Required for local operator login and JWT verification.
- `LOCAL_AUTH_ENABLED=true`
  Enables the pilot bootstrap login for the admin console.
- `PILOT_BOOTSTRAP_ADMIN_EMAIL`
- `PILOT_BOOTSTRAP_ADMIN_PASSWORD`
- `PILOT_BOOTSTRAP_ORG_NAME`
- `PILOT_BOOTSTRAP_ORG_SLUG`
- `COMMAND_SIGNING_PRIVATE_KEY_PATH`
- `COMMAND_SIGNING_PUBLIC_KEY_PATH`
- `SIGNED_TELEMETRY_MODE=required`
- `ALLOW_PLACEHOLDER_SIGNED_TELEMETRY=false`
- `ALLOW_INSECURE_JWT_FOR_DEV=false`
- `OBJECT_STORAGE_BACKEND`
- `IP_ENRICHMENT_PROVIDER`
- `INTEGRITY_VERIFICATION_PROVIDER`
- `PLAY_INTEGRITY_EXPECTED_PACKAGE`

Recommended local values:

```env
JWT_SHARED_SECRET=change-me-for-local-pilot
LOCAL_AUTH_ENABLED=true
PILOT_BOOTSTRAP_ADMIN_EMAIL=admin@trackme.local
PILOT_BOOTSTRAP_ADMIN_PASSWORD=pilot-password-123
PILOT_BOOTSTRAP_ADMIN_NAME=Pilot Admin
PILOT_BOOTSTRAP_ADMIN_ROLE=admin
PILOT_BOOTSTRAP_ORG_NAME=TrackMe Pilot Org
PILOT_BOOTSTRAP_ORG_SLUG=trackme-pilot
COMMAND_SIGNING_PRIVATE_KEY_PATH=/app/.secrets/command_signing_private.pem
COMMAND_SIGNING_PUBLIC_KEY_PATH=/app/.secrets/command_signing_public.pem
OBJECT_STORAGE_BACKEND=local
OBJECT_STORAGE_LOCAL_DIR=/app/object_storage
IP_ENRICHMENT_PROVIDER=none
INTEGRITY_VERIFICATION_PROVIDER=none
PLAY_INTEGRITY_EXPECTED_PACKAGE=com.example.trackme
```

If you run outside Docker, use local filesystem paths instead:

```env
COMMAND_SIGNING_PRIVATE_KEY_PATH=/home/haroon/AndroidStudioProjects/TrackMe/backend/.secrets/command_signing_private.pem
COMMAND_SIGNING_PUBLIC_KEY_PATH=/home/haroon/AndroidStudioProjects/TrackMe/backend/.secrets/command_signing_public.pem
```

## 3. Start the backend stack

### Docker Compose

This is the easiest local path because it starts:

- PostGIS
- Redis
- API
- worker

```bash
cd /home/haroon/AndroidStudioProjects/TrackMe/backend
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- OpenAPI: `http://localhost:8000/docs`
- Worker: runs continuously in `trackme-worker`

### Without Docker

```bash
cd /home/haroon/AndroidStudioProjects/TrackMe/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd /home/haroon/AndroidStudioProjects/TrackMe/backend
source .venv/bin/activate
python -m app.worker
```

## 4. Start the admin console

```bash
cd /home/haroon/AndroidStudioProjects/TrackMe/admin-console
cp .env.example .env.local
npm install
npm run dev
```

Use these values in `admin-console/.env.local`:

```env
NEXT_PUBLIC_USE_MOCKS=false
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_MAP_PROVIDER=google
NEXT_PUBLIC_GOOGLE_STATIC_MAPS_API_KEY=
NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN=
```

Open:

```text
http://localhost:3000/login
```

Log in with the bootstrap admin credentials from the backend `.env`.

## 5. Point Android at the same backend

TrackMe Android now reads the backend URL and command verification public key from Gradle properties.

Add these to `~/.gradle/gradle.properties` or a project-level `gradle.properties`:

```properties
TRACKME_API_BASE_URL=http://10.0.2.2:8000/api/
TRACKME_COMMAND_VERIFICATION_PUBLIC_KEY_PEM=-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----
TRACKME_MAP_PROVIDER=google
TRACKME_GOOGLE_STATIC_MAPS_API_KEY=
TRACKME_MAPBOX_ACCESS_TOKEN=
TRACKME_MAPBOX_USERNAME=mapbox
TRACKME_MAPBOX_STYLE_ID=streets-v12
```

Important:

- `10.0.2.2` works for an Android emulator.
- for a real phone on USB/Wi-Fi, replace it with your computer's LAN IP such as `http://192.168.x.x:8000/api/`

For local debug builds, cleartext HTTP is enabled in `app/src/debug/AndroidManifest.xml`.

Build and install:

```bash
cd /home/haroon/AndroidStudioProjects/TrackMe
./gradlew :app:installDebug
```

## 6. Run the pilot flow end to end

### Operator enrollment

1. Log in to the admin console.
2. Open `Support Queue`.
3. Use the `Device enrollment issuance` card.
4. Choose:
   - ownership type
   - enrollment type
   - optional existing device
   - owner subject for single-user enrollment
5. Click `Issue enrollment token`.
6. Copy the token or pairing link.

### Phone enrollment

1. Open the Android app.
2. Go through disclosure and consent.
3. On the `Device Enrollment` screen, paste the token or pairing link.
4. Complete enrollment.

### Verify telemetry

1. Keep the phone online.
2. Wait for a check-in or trigger the relevant action in the app.
3. In the admin console:
   - open `Device Inventory`
   - open the device details page
   - confirm last check-in and location quality

### Run an incident

1. Open `Incidents`.
2. Mark a device as lost.
3. Confirm the case appears in `Support Queue`.
4. Review:
   - timeline
   - route
   - evidence chain
   - command attempts

### Verify background processing

The worker should:

- process queued rule events
- schedule stale/offline incident checks
- re-evaluate pending command retry/expiry flows

Check worker logs for event processing activity.

## 7. Notifications

Push delivery requires valid Firebase credentials and device push tokens.

Behavior now:

- no silent fake delivery
- missing FCM configuration becomes an explicit failed notification record
- incident escalations create internal alert records instead of using fake tokens

For live device push:

1. configure `FCM_SERVER_KEY` in backend `.env`
2. ensure Android receives and registers a valid FCM token
3. keep the worker and API running

## 8. Maps, storage, IP enrichment, and integrity providers

TrackMe now supports pluggable provider configuration for these pilot-hardening paths.

### Maps

- Admin console:
  - `NEXT_PUBLIC_MAP_PROVIDER=google` or `mapbox`
  - `NEXT_PUBLIC_GOOGLE_STATIC_MAPS_API_KEY`
  - `NEXT_PUBLIC_MAPBOX_ACCESS_TOKEN`
  - `NEXT_PUBLIC_MAPBOX_USERNAME`
  - `NEXT_PUBLIC_MAPBOX_STYLE_ID`
- Android:
  - `TRACKME_MAP_PROVIDER=google` or `mapbox`
  - `TRACKME_GOOGLE_STATIC_MAPS_API_KEY`
  - `TRACKME_MAPBOX_ACCESS_TOKEN`
  - `TRACKME_MAPBOX_USERNAME`
  - `TRACKME_MAPBOX_STYLE_ID`

Current implementation note:

- the pilot now uses real provider-backed static map rendering
- if credentials are missing, both Android and web fall back to their local placeholder renderer
- approximate, stale, and offline states remain visually distinct

### Evidence storage

- `OBJECT_STORAGE_BACKEND=local` for local pilots
- `OBJECT_STORAGE_BACKEND=s3` for S3-compatible storage
- When using S3-compatible storage, configure:
  - `OBJECT_STORAGE_S3_BUCKET`
  - `OBJECT_STORAGE_S3_REGION`
  - `OBJECT_STORAGE_S3_ENDPOINT`
  - `OBJECT_STORAGE_S3_ACCESS_KEY`
  - `OBJECT_STORAGE_S3_SECRET_KEY`
  - `OBJECT_STORAGE_S3_PREFIX`

### IP enrichment

- `IP_ENRICHMENT_PROVIDER=none`, `ipinfo`, or `ipapi`
- `IP_ENRICHMENT_API_URL`
- `IP_ENRICHMENT_API_KEY`
- `IP_ENRICHMENT_CACHE_TTL_SECONDS`

Important:

- IP-derived location remains approximate only
- if the provider is unavailable or rate-limited, the backend falls back gracefully without claiming a live coordinate

### Integrity

- `INTEGRITY_VERIFICATION_PROVIDER=none` or `play_integrity`
- `PLAY_INTEGRITY_EXPECTED_PACKAGE=com.example.trackme`

Current implementation note:

- the backend now understands verified/advisory/unavailable/suspicious integrity outcomes
- Android exposes honest advisory integrity-provider state
- full production Play Integrity verification still requires upstream verifier wiring and credentials

## 9. Validation commands

Run these from the repo root:

```bash
cd /home/haroon/AndroidStudioProjects/TrackMe
PYTHONPATH=backend pytest -q backend/tests
./gradlew testDebugUnitTest
./gradlew :app:assembleDebug
cd admin-console && npm run typecheck && npm run build
```

## Current known pilot gaps

- Android and web currently use real provider-backed static maps, not full interactive SDK map clients
- integrity verification is still advisory unless a real Play Integrity verifier is wired in
- live IP enrichment and map rendering still depend on real provider credentials
- operator-facing notification inbox/history is still thinner than the backend event model
