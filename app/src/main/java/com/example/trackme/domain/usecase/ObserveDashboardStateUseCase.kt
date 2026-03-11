package com.example.trackme.domain.usecase

import com.example.trackme.domain.model.DashboardState
import com.example.trackme.domain.repository.DeviceStateRepository
import com.example.trackme.domain.repository.EnrollmentRepository
import com.example.trackme.domain.repository.LocationRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import javax.inject.Inject

class ObserveDashboardStateUseCase @Inject constructor(
    private val enrollmentRepository: EnrollmentRepository,
    private val deviceStateRepository: DeviceStateRepository,
    private val locationRepository: LocationRepository
) {
    operator fun invoke(): Flow<DashboardState> {
        return combine(
            enrollmentRepository.observeEnrollmentStatus(),
            deviceStateRepository.observeDeviceState(),
            locationRepository.observeLastKnownLocation()
        ) { enrollment, deviceState, location ->
            DashboardState(enrollment = enrollment, deviceState = deviceState, lastLocation = location)
        }
    }
}
