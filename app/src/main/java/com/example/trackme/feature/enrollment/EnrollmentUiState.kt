package com.example.trackme.feature.enrollment

import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.model.EnrollmentAuthorizationRole
import com.example.trackme.domain.model.OwnershipType
import com.example.trackme.domain.model.PairingMethod

data class EnrollmentForm(
    val organizationName: String = "",
    val deviceAlias: String = "",
    val ownerSubject: String = "",
    val pairingCredential: String = "",
    val ownershipType: OwnershipType = OwnershipType.SINGLE_USER,
    val authorizationRole: EnrollmentAuthorizationRole = EnrollmentAuthorizationRole.OWNER,
    val pairingMethod: PairingMethod = PairingMethod.ENROLLMENT_TOKEN,
    val authorizationConfirmed: Boolean = false,
    val isSubmitting: Boolean = false,
    val errorMessage: String? = null
)

typealias EnrollmentUiState = AsyncUiState<EnrollmentForm>
