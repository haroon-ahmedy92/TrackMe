package com.example.trackme.feature.enrollment

import com.example.trackme.core.ui.AsyncUiState

data class EnrollmentForm(
    val organizationName: String = "",
    val authorizationConfirmed: Boolean = false,
    val isSubmitting: Boolean = false,
    val errorMessage: String? = null
)

typealias EnrollmentUiState = AsyncUiState<EnrollmentForm>
