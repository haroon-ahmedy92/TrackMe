# TrackMe App Layer

This package contains app entry points:

- `TrackMeApplication`: Hilt + WorkManager initialization.
- `MainActivity`: visible launcher activity and runtime permission flow.

Design intent:
- Keep app behavior explicit and user-visible.
- Route all business logic through `domain` use cases.
- Keep legal/consent decisions centralized in `compliance`.
