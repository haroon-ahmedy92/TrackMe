package com.example.trackme.location

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class LocationSpoofingDetectorTest {

    private val detector = LocationSpoofingDetector()

    @Test
    fun `mock provider is marked suspicious`() {
        val result = detector.assess(
            signal = SpoofingSignal(
                isMockProvider = true,
                capturedAtEpochMs = 1_000L,
                accuracyMeters = 20f,
                speedMetersPerSecond = 2f
            ),
            nowEpochMs = 2_000L
        )

        assertTrue(result.suspicious)
        assertTrue(result.reasonCodes.contains("FLAGGED_MOCK_PROVIDER"))
    }

    @Test
    fun `unrealistic speed with high confidence is marked suspicious`() {
        val result = detector.assess(
            signal = SpoofingSignal(
                isMockProvider = false,
                capturedAtEpochMs = 10_000L,
                accuracyMeters = 30f,
                speedMetersPerSecond = 120f
            ),
            nowEpochMs = 11_000L
        )

        assertTrue(result.suspicious)
        assertTrue(result.reasonCodes.contains("UNREALISTIC_SPEED"))
    }

    @Test
    fun `normal signal is not suspicious`() {
        val result = detector.assess(
            signal = SpoofingSignal(
                isMockProvider = false,
                capturedAtEpochMs = 100_000L,
                accuracyMeters = 50f,
                speedMetersPerSecond = 1.5f
            ),
            nowEpochMs = 110_000L
        )

        assertFalse(result.suspicious)
        assertTrue(result.reasonCodes.isEmpty())
    }
}
