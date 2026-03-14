package com.example.trackme.telemetry

import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.min

@Singleton
class TelemetryRetryPolicy @Inject constructor() {
    fun nextRetryEpochMs(nowEpochMs: Long, attemptCount: Int): Long {
        val boundedAttempt = attemptCount.coerceAtLeast(1)
        val delayMs = min(INITIAL_BACKOFF_MS * (1L shl (boundedAttempt - 1)), MAX_BACKOFF_MS)
        return nowEpochMs + delayMs
    }

    companion object {
        private const val INITIAL_BACKOFF_MS = 60_000L
        private const val MAX_BACKOFF_MS = 6 * 60 * 60_000L
    }
}
