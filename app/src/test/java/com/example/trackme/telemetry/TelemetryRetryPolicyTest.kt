package com.example.trackme.telemetry

import org.junit.Assert.assertEquals
import org.junit.Test

class TelemetryRetryPolicyTest {

    @Test
    fun nextRetryEpochMs_appliesExponentialBackoff() {
        val policy = TelemetryRetryPolicy()
        val now = 1_710_000_000_000L

        assertEquals(now + 60_000L, policy.nextRetryEpochMs(now, attemptCount = 1))
        assertEquals(now + 120_000L, policy.nextRetryEpochMs(now, attemptCount = 2))
        assertEquals(now + 240_000L, policy.nextRetryEpochMs(now, attemptCount = 3))
    }
}
