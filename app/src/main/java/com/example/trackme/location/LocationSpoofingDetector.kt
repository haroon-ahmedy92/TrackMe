package com.example.trackme.location

import javax.inject.Inject

data class SpoofingAssessment(
    val suspicious: Boolean,
    val reasonCodes: List<String>
)

data class SpoofingSignal(
    val isMockProvider: Boolean,
    val capturedAtEpochMs: Long,
    val accuracyMeters: Float,
    val speedMetersPerSecond: Float?
)

class LocationSpoofingDetector @Inject constructor() {
    fun assess(signal: SpoofingSignal, nowEpochMs: Long): SpoofingAssessment {
        val reasons = buildList {
            if (signal.isMockProvider) add("FLAGGED_MOCK_PROVIDER")
            if (signal.capturedAtEpochMs > nowEpochMs + FUTURE_TIMESTAMP_TOLERANCE_MS) {
                add("FUTURE_TIMESTAMP")
            }
            val speed = signal.speedMetersPerSecond
            if (speed != null && speed > MAX_REALISTIC_SPEED_MPS && signal.accuracyMeters <= 120f) {
                add("UNREALISTIC_SPEED")
            }
        }

        return SpoofingAssessment(
            suspicious = reasons.isNotEmpty(),
            reasonCodes = reasons
        )
    }

    companion object {
        private const val FUTURE_TIMESTAMP_TOLERANCE_MS = 2 * 60_000L
        private const val MAX_REALISTIC_SPEED_MPS = 95f
    }
}
