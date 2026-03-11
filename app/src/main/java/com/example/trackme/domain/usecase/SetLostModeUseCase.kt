package com.example.trackme.domain.usecase

import com.example.trackme.data.preferences.TrackingPreferencesDataSource
import com.example.trackme.domain.repository.AuditRepository
import com.example.trackme.domain.repository.DeviceStateRepository
import com.example.trackme.worker.CheckInScheduler
import javax.inject.Inject
import kotlinx.coroutines.flow.first

class SetLostModeUseCase @Inject constructor(
    private val deviceStateRepository: DeviceStateRepository,
    private val auditRepository: AuditRepository,
    private val trackingPreferences: TrackingPreferencesDataSource,
    private val checkInScheduler: CheckInScheduler
) {
    suspend fun enable(untilEpochMs: Long) {
        deviceStateRepository.setLostMode(untilEpochMs)
        val consentGranted = trackingPreferences.explicitTrackingConsentGranted.first()
        if (consentGranted) {
            checkInScheduler.scheduleLostModeCheckIn(untilEpochMs)
        }
        auditRepository.appendEvent(
            type = "LOST_MODE_ENABLED",
            summary = "Lost mode activated",
            metadata = mapOf(
                "untilEpochMs" to untilEpochMs.toString(),
                "consentGranted" to consentGranted.toString()
            )
        )
    }

    suspend fun disable() {
        deviceStateRepository.setLostMode(null)
        checkInScheduler.cancelLostModeCheckIn()
        auditRepository.appendEvent(
            type = "LOST_MODE_DISABLED",
            summary = "Lost mode deactivated"
        )
    }
}
