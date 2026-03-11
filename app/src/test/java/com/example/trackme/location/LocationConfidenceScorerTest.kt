package com.example.trackme.location

import com.example.trackme.domain.model.LocationPrecision
import com.example.trackme.domain.model.MotionState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LocationConfidenceScorerTest {

    private val scorer = LocationConfidenceScorer()

    @Test
    fun `precise fresh signal scores higher than approximate stale signal`() {
        val now = 1_000_000L

        val precise = scorer.score(
            accuracyMeters = 20f,
            capturedAtEpochMs = now,
            nowEpochMs = now,
            isApproximate = false
        )
        val approximate = scorer.score(
            accuracyMeters = 800f,
            capturedAtEpochMs = now - 20 * 60_000L,
            nowEpochMs = now,
            isApproximate = true
        )

        assertTrue(precise > approximate)
    }

    @Test
    fun `score is clamped to expected range`() {
        val score = scorer.score(
            accuracyMeters = 9_999f,
            capturedAtEpochMs = 0L,
            nowEpochMs = 100 * 60_000L,
            isApproximate = true
        )

        assertTrue(score in 5..99)
    }

    @Test
    fun `suspicious mock signal is heavily penalized`() {
        val now = 1_000_000L
        val clean = scorer.score(
            accuracyMeters = 30f,
            capturedAtEpochMs = now,
            nowEpochMs = now,
            isApproximate = false,
            sourceCount = 3,
            hasRecentGeofenceEvent = true,
            motionState = MotionState.ON_FOOT,
            suspiciousMock = false
        )
        val suspicious = scorer.score(
            accuracyMeters = 30f,
            capturedAtEpochMs = now,
            nowEpochMs = now,
            isApproximate = false,
            sourceCount = 3,
            hasRecentGeofenceEvent = true,
            motionState = MotionState.ON_FOOT,
            suspiciousMock = true
        )

        assertTrue(clean > suspicious)
    }

    @Test
    fun `precision classification aligns with accuracy and approximation`() {
        assertEquals(
            LocationPrecision.PRECISE,
            scorer.classifyPrecision(accuracyMeters = 25f, isApproximate = false)
        )
        assertEquals(
            LocationPrecision.MODERATE,
            scorer.classifyPrecision(accuracyMeters = 180f, isApproximate = false)
        )
        assertEquals(
            LocationPrecision.APPROXIMATE,
            scorer.classifyPrecision(accuracyMeters = 20f, isApproximate = true)
        )
    }
}
