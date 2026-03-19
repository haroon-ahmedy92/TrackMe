package com.example.trackme.feature.map

import android.content.ContextWrapper
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.model.CheckInMode
import com.example.trackme.domain.model.DashboardState
import com.example.trackme.domain.model.DeviceState
import com.example.trackme.domain.model.EnrollmentStatus
import com.example.trackme.domain.model.LocationPrecision
import com.example.trackme.domain.model.LocationSnapshot
import com.example.trackme.domain.model.MotionState
import com.example.trackme.domain.model.NetworkType
import com.example.trackme.domain.repository.DeviceStateRepository
import com.example.trackme.domain.repository.EnrollmentRepository
import com.example.trackme.domain.repository.IntegrityRepository
import com.example.trackme.domain.repository.LocationRepository
import com.example.trackme.domain.usecase.ObserveDashboardStateUseCase
import com.example.trackme.testing.MainDispatcherRule
import com.example.trackme.trust.AppTrustSignalCollector
import com.example.trackme.trust.AppTrustSignals
import com.example.trackme.trust.DeviceTrustEvaluator
import com.example.trackme.trust.DeviceTrustStatus
import com.example.trackme.trust.DeviceTrustSummary
import com.example.trackme.trust.IntegritySignal
import com.example.trackme.ui.map.MapProvider
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class MapViewModelTest {

    @get:Rule
    val mainDispatcherRule = MainDispatcherRule()

    @Test
    fun mapViewModel_combinesDashboardAndRecentHistory() = runTest {
        val dashboardState = DashboardState(
            enrollment = EnrollmentStatus(isEnrolled = true, organizationName = "Org", consentVersion = "1", enrolledAtEpochMs = 1L),
            deviceState = DeviceState(mode = CheckInMode.NORMAL, lastCheckInEpochMs = 2L, batteryPercent = 80, lostModeUntilEpochMs = null),
            lastLocation = sampleLocation(epochMs = 2_000L),
            trustSummary = sampleTrustSummary(),
        )
        val repository = FakeLocationRepository(history = listOf(sampleLocation(epochMs = 1_000L), sampleLocation(epochMs = 2_000L)))
        val viewModel = MapViewModel(
            observeDashboardStateUseCase = ObserveDashboardStateUseCase(
                enrollmentRepository = FakeEnrollmentRepository(dashboardState.enrollment),
                deviceStateRepository = FakeDeviceStateRepository(dashboardState.deviceState),
                locationRepository = repository,
                integrityRepository = FakeIntegrityRepository(),
                appTrustSignalCollector = FakeAppTrustSignalCollector(),
                deviceTrustEvaluator = FakeDeviceTrustEvaluator(dashboardState.trustSummary),
            ),
            locationRepository = repository,
            mapProvider = FakeMapProvider()
        )

        advanceUntilIdle()

        val state = viewModel.uiState.value
        assertTrue(state is AsyncUiState.Data)
        val content = (state as AsyncUiState.Data).value
        assertEquals(2, content.history.size)
        assertEquals(2_000L, content.dashboard.lastLocation?.capturedAtEpochMs)
    }
}

private class FakeLocationRepository(
    history: List<LocationSnapshot>
) : LocationRepository {
    private val historyFlow = MutableStateFlow(history)

    override fun observeLastKnownLocation(): Flow<LocationSnapshot?> = flowOf(historyFlow.value.lastOrNull())

    override fun observeRecentHistory(limit: Int): Flow<List<LocationSnapshot>> = historyFlow

    override suspend fun captureCurrentLocation(source: String): LocationSnapshot? = null
}

private class FakeEnrollmentRepository(
    private val status: EnrollmentStatus
) : EnrollmentRepository {
    override fun observeEnrollmentStatus(): Flow<EnrollmentStatus> = flowOf(status)

    override suspend fun enroll(request: com.example.trackme.domain.model.EnrollmentRequest): EnrollmentStatus = status
}

private class FakeDeviceStateRepository(
    private val state: DeviceState
) : DeviceStateRepository {
    override fun observeDeviceState(): Flow<DeviceState> = flowOf(state)

    override suspend fun updateCheckIn(mode: CheckInMode, batteryPercent: Int?, checkInAtEpochMs: Long) = Unit

    override suspend fun setLostMode(untilEpochMs: Long?) = Unit
}

private class FakeMapProvider : MapProvider {
    override val providerName: String = "fake"

    override fun formatMarkerTitle(location: LocationSnapshot): String = "marker"
}

private class FakeIntegrityRepository : IntegrityRepository {
    override suspend fun getIntegritySignal(): IntegritySignal = IntegritySignal(
        token = null,
        status = "unavailable",
        trusted = false,
        provider = "test",
    )

    override fun observeIntegritySignal(): Flow<IntegritySignal> = flowOf(
        IntegritySignal(token = null, status = "unavailable", trusted = false, provider = "test")
    )
}

private class FakeAppTrustSignalCollector : AppTrustSignalCollector(ContextWrapper(null)) {
    override fun collect(): AppTrustSignals {
        return AppTrustSignals(
            debugBuild = false,
            debuggableApp = false,
            testKeysBuild = false,
            suBinaryPresent = false,
        )
    }
}

private class FakeDeviceTrustEvaluator(
    private val summary: DeviceTrustSummary,
) : DeviceTrustEvaluator() {
    override fun assess(
        integritySignal: IntegritySignal,
        appSignals: AppTrustSignals,
        locationSnapshot: LocationSnapshot?,
        keyHardwareBacked: Boolean,
        attestationDeclared: Boolean,
    ): DeviceTrustSummary = summary
}

private fun sampleLocation(epochMs: Long) = LocationSnapshot(
    latitude = -6.7924,
    longitude = 39.2083,
    accuracyMeters = 14f,
    capturedAtEpochMs = epochMs,
    source = "test",
    methodLabel = "Fused GPS",
    isApproximate = false,
    confidenceScore = 90,
    precision = LocationPrecision.PRECISE,
    sourceSignals = listOf("fused_gps"),
    batteryLevelPercent = 80,
    networkType = NetworkType.WIFI,
    motionState = MotionState.STILL
)

private fun sampleTrustSummary() = DeviceTrustSummary(
    status = DeviceTrustStatus.TRUSTED,
    headline = "Advisory trust signals look healthy",
    details = "Signed telemetry and current device signals do not show obvious issues. This is advisory, not proof.",
    reasons = emptyList(),
    integrityStatus = "trusted_placeholder",
    integrityTrusted = true,
    debugBuild = false,
    debuggableApp = false,
    rootSuspicion = false,
    mockLocationSuspicion = false,
    keyHardwareBacked = true,
    attestationDeclared = true,
    integrityTokenPresent = true,
)
