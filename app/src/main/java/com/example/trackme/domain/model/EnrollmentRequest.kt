package com.example.trackme.domain.model

data class EnrollmentRequest(
    val organizationName: String,
    val consentVersion: String,
    val deviceAlias: String,
    val ownerSubject: String?,
    val ownershipType: OwnershipType,
    val authorizationRole: EnrollmentAuthorizationRole,
    val pairingCredential: String,
    val pairingMethod: PairingMethod
)
