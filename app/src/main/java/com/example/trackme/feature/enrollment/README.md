# Enrollment Feature

This package handles explicit device enrollment on Android.

Main responsibilities:
- collect visible ownership and pairing details
- explain what enrollment means
- generate a device keypair for backend identity registration
- call the backend pairing endpoint when available
- keep the UI simple enough for a student to follow

Key files:
- `DeviceEnrollmentScreen.kt`: Compose UI for the visible flow.
- `EnrollmentViewModel.kt`: form state, validation, and submission.
- `EnrollmentCoordinator.kt`: thin seam that keeps the ViewModel testable.

Important product rule:
this flow is explicit and visible. It does not hide the app, silently enable tracking, or bypass Android permission rules.
