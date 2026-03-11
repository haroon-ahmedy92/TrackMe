package com.example.trackme.location

import com.example.trackme.domain.model.LocationPrecision
import com.example.trackme.domain.model.MotionState
import javax.inject.Inject

class LocationConfidenceScorer @Inject constructor() {
    fun score(
        accuracyMeters: Float,
        capturedAtEpochMs: Long,
        nowEpochMs: Long,
        isApproximate: Boolean,
        sourceCount: Int = 1,
        hasRecentGeofenceEvent: Boolean = false,
        motionState: MotionState = MotionState.UNKNOWN,
        suspiciousMock: Boolean = false
    ): Int {
        val accuracyScore = when {
            accuracyMeters <= 25f -> 95
            accuracyMeters <= 75f -> 85
            accuracyMeters <= 150f -> 75
            accuracyMeters <= 500f -> 60
            accuracyMeters <= 1_000f -> 45
            else -> 30
        }
        val ageMinutes = ((nowEpochMs - capturedAtEpochMs).coerceAtLeast(0) / 60_000L).toInt()
        val agePenalty = (ageMinutes * 2).coerceAtMost(35)
        val approximationPenalty = if (isApproximate) 12 else 0
        val sourceBonus = ((sourceCount - 1).coerceAtLeast(0) * 2).coerceAtMost(8)
        val geofenceBonus = if (hasRecentGeofenceEvent) 4 else 0
        val motionBonus = if (motionState == MotionState.UNKNOWN) 0 else 3
        val spoofingPenalty = if (suspiciousMock) 30 else 0
        return (accuracyScore - agePenalty - approximationPenalty + sourceBonus + geofenceBonus + motionBonus - spoofingPenalty)
            .coerceIn(5, 99)
    }

    fun classifyPrecision(
        accuracyMeters: Float,
        isApproximate: Boolean
    ): LocationPrecision {
        if (isApproximate) return LocationPrecision.APPROXIMATE
        return when {
            accuracyMeters <= 60f -> LocationPrecision.PRECISE
            accuracyMeters <= 250f -> LocationPrecision.MODERATE
            else -> LocationPrecision.APPROXIMATE
        }
    }
}
