package com.example.trackme.telemetry

import com.example.trackme.domain.model.CheckInMode
import com.example.trackme.domain.model.NetworkType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TelemetrySyncPolicyTest {

    @Test
    fun resolve_usesLargerBatchOnWifi() {
        val policy = TelemetrySyncPolicy().resolve(NetworkType.WIFI, listOf(CheckInMode.NORMAL))

        assertTrue(policy.shouldSync)
        assertEquals(25, policy.maxBatchSize)
    }

    @Test
    fun resolve_usesSmallerBatchOnCellularUnlessLostMode() {
        val normal = TelemetrySyncPolicy().resolve(NetworkType.CELLULAR, listOf(CheckInMode.NORMAL))
        val lost = TelemetrySyncPolicy().resolve(NetworkType.CELLULAR, listOf(CheckInMode.LOST_MODE))

        assertEquals(5, normal.maxBatchSize)
        assertEquals(10, lost.maxBatchSize)
    }

    @Test
    fun resolve_disablesSyncWhenOffline() {
        val policy = TelemetrySyncPolicy().resolve(NetworkType.NONE, listOf(CheckInMode.NORMAL))

        assertFalse(policy.shouldSync)
        assertEquals(0, policy.maxBatchSize)
    }
}
