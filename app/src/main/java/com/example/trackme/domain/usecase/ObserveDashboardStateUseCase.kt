package com.example.trackme.domain.usecase

import com.example.trackme.domain.model.DashboardState
import com.example.trackme.domain.repository.DeviceStateRepository
import com.example.trackme.domain.repository.EnrollmentRepository
import com.example.trackme.domain.repository.IntegrityRepository
import com.example.trackme.domain.repository.LocationRepository
import com.example.trackme.trust.AppTrustSignalCollector
import com.example.trackme.trust.DeviceTrustEvaluator
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import javax.inject.Inject

class ObserveDashboardStateUseCase @Inject constructor(
    private val enrollmentRepository: EnrollmentRepository,
    private val deviceStateRepository: DeviceStateRepository,
    private val locationRepository: LocationRepository,
    private val integrityRepository: IntegrityRepository,
    private val appTrustSignalCollector: AppTrustSignalCollector,
    private val deviceTrustEvaluator: DeviceTrustEvaluator,
) {
    operator fun invoke(): Flow<DashboardState> {
        return combine(
            enrollmentRepository.observeEnrollmentStatus(),
            deviceStateRepository.observeDeviceState(),
            locationRepository.observeLastKnownLocation(),
            integrityRepository.observeIntegritySignal(),
        ) { enrollment, deviceState, location, integritySignal ->
            DashboardState(
                enrollment = enrollment,
                deviceState = deviceState,
                lastLocation = location,
                trustSummary = deviceTrustEvaluator.assess(
                    integritySignal = integritySignal,
                    appSignals = appTrustSignalCollector.collect(),
                    locationSnapshot = location,
                    keyHardwareBacked = enrollment.keyHardwareBacked == true,
                    attestationDeclared = !enrollment.keyAttestationFormat.isNullOrBlank(),
                ),
            )
        }
    }
}
