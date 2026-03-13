package com.example.trackme.domain.usecase

import com.example.trackme.core.TimeProvider
import com.example.trackme.data.preferences.TrackingPreferencesDataSource
import com.example.trackme.domain.model.EnrollmentRequest
import com.example.trackme.domain.model.EnrollmentStatus
import com.example.trackme.domain.repository.AuditRepository
import com.example.trackme.domain.repository.EnrollmentRepository
import javax.inject.Inject

open class EnrollDeviceUseCase @Inject constructor(
    private val enrollmentRepository: EnrollmentRepository,
    private val auditRepository: AuditRepository,
    private val trackingPreferences: TrackingPreferencesDataSource,
    private val timeProvider: TimeProvider
) {
    open suspend operator fun invoke(request: EnrollmentRequest): EnrollmentStatus {
        trackingPreferences.grantExplicitTrackingConsent(
            consentVersion = request.consentVersion,
            acceptedAtEpochMs = timeProvider.nowEpochMillis()
        )
        val status = enrollmentRepository.enroll(request)
        auditRepository.appendEvent(
            type = "ENROLLMENT_ACCEPTED",
            summary = "Device enrolled for organization recovery",
            metadata = mapOf(
                "organizationName" to request.organizationName,
                "consentVersion" to request.consentVersion,
                "ownershipType" to request.ownershipType.name,
                "authorizationRole" to request.authorizationRole.name,
                "pairingMethod" to request.pairingMethod.name,
                "deviceAlias" to request.deviceAlias,
                "ownerSubject" to (request.ownerSubject ?: ""),
                "explicitTrackingConsentGranted" to "true",
                "registrationState" to status.registrationState.name,
            )
        )
        return status
    }
}
