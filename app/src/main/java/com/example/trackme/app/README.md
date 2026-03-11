# App Layer

Owns app-level navigation and shell state.

- `TrackMeRootApp`: single navigation graph for onboarding + managed flows.
- `AppShellViewModel`: app entry state (enrolled vs not enrolled).

Permission requests are not triggered here automatically; they happen in explicit onboarding education screens.
