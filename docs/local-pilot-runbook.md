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

## 8. Validation commands

Run these from the repo root:

```bash
cd /home/haroon/AndroidStudioProjects/TrackMe
PYTHONPATH=backend pytest -q backend/tests
./gradlew testDebugUnitTest
./gradlew :app:assembleDebug
cd admin-console && npm run typecheck && npm run build
```

## Current known pilot gaps

- map providers are still placeholder visual layers, not Google Maps/Mapbox integrations
- integrity verification is still advisory/placeholder beyond signing and key checks
- IP enrichment is still not backed by a real provider
- attachment storage still needs a stronger durable abstraction for long-running evidence handling
- operator-facing notification inbox/history is still thinner than the backend event model
