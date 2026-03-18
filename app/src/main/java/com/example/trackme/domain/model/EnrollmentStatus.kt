package com.example.trackme.domain.model

data class EnrollmentStatus(
    val isEnrolled: Boolean,
    val organizationName: String?,
    val consentVersion: String?,
    val enrolledAtEpochMs: Long?,
    val deviceAlias: String? = null,
    val orgId: String? = null,
    val deviceId: String? = null,
    val ownershipBindingId: String? = null,
    val ownerSubject: String? = null,
    val ownershipType: OwnershipType? = null,
    val authorizationRole: EnrollmentAuthorizationRole? = null,
    val pairingMethod: PairingMethod? = null,
    val keyId: String? = null,
    val keyAlgorithm: String? = null,
    val keyHardwareBacked: Boolean? = null,
    val keyAttestationFormat: String? = null,
    val registrationState: RegistrationState = RegistrationState.PENDING_BACKEND_VERIFICATION
)
