# Location Package

Contains location provider abstractions and Android implementation.

Behavior:
- Reads location only when normal Android permissions are granted.
- Combines lawful signals (fused, GPS provider, network provider, optional IP-derived approximation, geofence-event context, motion context, and network context).
- Produces `confidenceScore` and `precision` (`PRECISE`, `MODERATE`, `APPROXIMATE`) for every location sample.
- Labels backend/IP methods as approximate only, never exact.
- Captures battery %, network type, motion state, hashed Wi-Fi identifiers (when lawful), spoofing heuristics, and Wi-Fi RTT capability flag.
- Returns `null` when permission/location is unavailable.
- No hidden collection paths.

Key files:
- `LocationFusionEngine.kt`: main fusion and scoring pipeline.
- `LocationConfidenceScorer.kt`: confidence and precision logic.
- `LocationSpoofingDetector.kt`: suspicious mock-location heuristics hook.
- `NetworkContextCollector.kt`: lawful network and hashed Wi-Fi context collection.
