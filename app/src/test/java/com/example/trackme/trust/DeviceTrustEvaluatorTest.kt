package com.example.trackme.trust

import com.example.trackme.domain.model.LocationPrecision
import com.example.trackme.domain.model.LocationSnapshot
import com.example.trackme.domain.model.MotionState
import com.example.trackme.domain.model.NetworkType
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class DeviceTrustEvaluatorTest {

    private val evaluator = DeviceTrustEvaluator()

    @Test
    fun assess_returnsCautionWhenMockLocationAndDebugSignalsAppear() {
        val summary = evaluator.assess(
            integritySignal = IntegritySignal(
                token = null,
                status = "unavailable",
                trusted = false,
                provider = "placeholder",
                message = "Unavailable in unit test",
            ),
            appSignals = AppTrustSignals(
                debugBuild = false,
                debuggableApp = true,
                testKeysBuild = false,
                suBinaryPresent = false,
            ),
            locationSnapshot = sampleLocation(suspiciousMock = true),
            keyHardwareBacked = false,
            attestationDeclared = false,
        )

        assertEquals(DeviceTrustStatus.CAUTION, summary.status)
        assertTrue(summary.reasons.contains("MOCK_LOCATION_HEURISTIC"))
        assertTrue(summary.reasons.contains("DEBUGGABLE_APP_FLAG"))
    }

    @Test
    fun assess_returnsTrustedWhenIntegrityTrustedAndNoCautionSignals() {
        val summary = evaluator.assess(
            integritySignal = IntegritySignal(
                token = "token",
                status = "verified",
                trusted = true,
                provider = "placeholder",
                message = "Verified in unit test",
            ),
            appSignals = AppTrustSignals(
                debugBuild = false,
                debuggableApp = false,
                testKeysBuild = false,
                suBinaryPresent = false,
            ),
            locationSnapshot = sampleLocation(suspiciousMock = false),
            keyHardwareBacked = true,
            attestationDeclared = true,
        )

        assertEquals(DeviceTrustStatus.TRUSTED, summary.status)
        assertTrue(summary.reasons.isEmpty())
    }

    private fun sampleLocation(suspiciousMock: Boolean): LocationSnapshot {
        return LocationSnapshot(
            latitude = -6.7924,
            longitude = 39.2083,
            accuracyMeters = 20f,
            capturedAtEpochMs = 1_710_000_000_000L,
            source = "unit-test",
            methodLabel = "Fused location",
            isApproximate = false,
            confidenceScore = 84,
            precision = LocationPrecision.PRECISE,
            sourceSignals = listOf("fused_last_known"),
            batteryLevelPercent = 78,
            networkType = NetworkType.WIFI,
            motionState = MotionState.STILL,
            hashedWifiSsid = null,
            hashedWifiBssid = null,
            geofenceTransition = null,
            wifiRttCapable = false,
            suspiciousMockLocation = suspiciousMock,
            spoofingReasons = if (suspiciousMock) listOf("FLAGGED_MOCK_PROVIDER") else emptyList(),
        )
    }
}
