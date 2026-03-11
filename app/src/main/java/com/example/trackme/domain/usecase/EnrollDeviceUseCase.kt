package com.example.trackme.domain.usecase

import com.example.trackme.core.TimeProvider
import com.example.trackme.data.preferences.TrackingPreferencesDataSource
import com.example.trackme.domain.repository.AuditRepository
import com.example.trackme.domain.repository.EnrollmentRepository
import javax.inject.Inject

class EnrollDeviceUseCase @Inject constructor(
    private val enrollmentRepository: EnrollmentRepository,
    private val auditRepository: AuditRepository,
    private val trackingPreferences: TrackingPreferencesDataSource,
    private val timeProvider: TimeProvider
) {
    suspend operator fun invoke(organizationName: String, consentVersion: String) {
        trackingPreferences.grantExplicitTrackingConsent(
            consentVersion = consentVersion,
            acceptedAtEpochMs = timeProvider.nowEpochMillis()
        )
        enrollmentRepository.enroll(organizationName, consentVersion)
        auditRepository.appendEvent(
            type = "ENROLLMENT_ACCEPTED",
            summary = "Device enrolled for organization recovery",
            metadata = mapOf(
                "organizationName" to organizationName,
                "consentVersion" to consentVersion,
                "explicitTrackingConsentGranted" to "true"
            )
        )
    }
}
