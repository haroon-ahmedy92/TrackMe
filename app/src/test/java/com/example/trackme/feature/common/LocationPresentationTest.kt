package com.example.trackme.feature.common

import com.example.trackme.domain.model.LocationPrecision
import com.example.trackme.domain.model.LocationSnapshot
import com.example.trackme.domain.model.NetworkType
import org.junit.Assert.assertEquals
import org.junit.Test

class LocationPresentationTest {

    @Test
    fun `offline network marks sample offline`() {
        val sample = sample(networkType = NetworkType.NONE, capturedAtEpochMs = 1_000L)

        assertEquals(LocationFreshness.OFFLINE, sample.freshness(nowEpochMs = 10_000L))
    }

    @Test
    fun `old sample marks stale`() {
        val sample = sample(capturedAtEpochMs = 1_000L)

        assertEquals(LocationFreshness.STALE, sample.freshness(nowEpochMs = 3_700_000L))
    }

    @Test
    fun `recent sample stays recent`() {
        val sample = sample(capturedAtEpochMs = 1_000L)

        assertEquals(LocationFreshness.RECENT, sample.freshness(nowEpochMs = 20_000L))
    }

    private fun sample(
        networkType: NetworkType = NetworkType.CELLULAR,
        capturedAtEpochMs: Long,
    ) = LocationSnapshot(
        latitude = -6.8,
        longitude = 39.2,
        accuracyMeters = 24f,
        capturedAtEpochMs = capturedAtEpochMs,
        source = "fused",
        methodLabel = "Fused GPS",
        isApproximate = false,
        confidenceScore = 82,
        precision = LocationPrecision.MODERATE,
        networkType = networkType,
    )
}
