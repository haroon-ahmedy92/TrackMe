package com.example.trackme.app

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.trackme.commands.DeviceCommandSyncScheduler
import com.example.trackme.commands.PushTokenRegistrationCoordinator
import com.example.trackme.data.preferences.TrackingPreferencesDataSource
import com.example.trackme.domain.repository.EnrollmentRepository
import com.example.trackme.telemetry.TelemetrySyncScheduler
import com.example.trackme.worker.CheckInScheduler
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

@HiltViewModel
class AppShellViewModel @Inject constructor(
    enrollmentRepository: EnrollmentRepository,
    trackingPreferences: TrackingPreferencesDataSource,
    private val checkInScheduler: CheckInScheduler,
    private val commandSyncScheduler: DeviceCommandSyncScheduler,
    private val telemetrySyncScheduler: TelemetrySyncScheduler,
    private val pushTokenRegistrationCoordinator: PushTokenRegistrationCoordinator
) : ViewModel() {

    val isEnrolled: StateFlow<Boolean?> = combine(
        enrollmentRepository.observeEnrollmentStatus().map { it.isEnrolled },
        trackingPreferences.explicitTrackingConsentGranted
    ) { enrolled, consentGranted ->
        enrolled && consentGranted
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), null)

    fun ensureNormalScheduling() {
        viewModelScope.launch {
            checkInScheduler.scheduleNormalCheckIn()
            commandSyncScheduler.schedulePeriodicSync()
            telemetrySyncScheduler.schedulePeriodicSync()
            pushTokenRegistrationCoordinator.registerCurrentTokenIfAvailable()
        }
    }
}
