# Device Trust Signals

TrackMe now carries **advisory trust signals** from the Android app into backend telemetry and the admin console.

## Important framing

- These checks are **not proof of compromise**.
- A suspicious result means **review recommended**, not "the device is definitely rooted or tampered with."
- The app stays visible and policy-compliant. No hidden scans or covert behavior are introduced.

## What the Android app reports

The Android trust module collects a small, user-visible set of signals:

- debug build / debuggable-app placeholders
- simple root-suspicion placeholders such as `test-keys` or common `su` paths
- lawful mock-location heuristics already produced by the location fusion engine
- current integrity placeholder status
- whether the enrolled device key is declared hardware-backed

These signals are summarized into one advisory state:

- `trusted`
- `caution`
- `unavailable`

## What the backend does

On signed location ingest, the backend:

1. verifies the telemetry signature
2. normalizes the integrity placeholder result
3. combines the server-side verification result with the app-reported trust signals
4. stores:
   - per-event trust details on `location_events`
   - last-seen trust summary on `devices`

If the device trust status changes, the backend writes a separate immutable audit entry:

- `DEVICE_TRUST_UPDATED`

## What operators see

The admin console shows:

- a compact trust badge on inventory rows
- a trust card on the device detail page
- reason codes and explanatory text

The wording intentionally avoids certainty. "Needs review" means there are caution signals worth checking, not a confirmed compromise finding.
