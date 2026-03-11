package com.example.trackme.domain.usecase

import com.example.trackme.domain.repository.AuditRepository
import com.example.trackme.domain.repository.GeofenceRepository
import javax.inject.Inject

class SetGeofenceProtectionUseCase @Inject constructor(
    private val geofenceRepository: GeofenceRepository,
    private val auditRepository: AuditRepository
) {
    suspend operator fun invoke(enabled: Boolean, radiusMeters: Int) {
        geofenceRepository.setConfig(enabled = enabled, radiusMeters = radiusMeters)
        auditRepository.appendEvent(
            type = "GEOFENCE_CONFIG_UPDATED",
            summary = "Geofence protection configuration updated",
            metadata = mapOf(
                "enabled" to enabled.toString(),
                "radiusMeters" to radiusMeters.toString()
            )
        )
    }
}
