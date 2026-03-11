package com.example.trackme.ui.enrollment

import com.example.trackme.compliance.ConsentDisclosure

data class EnrollmentUiState(
    val organizationName: String = "",
    val consentAccepted: Boolean = false,
    val isSubmitting: Boolean = false,
    val isEnrolled: Boolean = false,
    val disclosure: ConsentDisclosure? = null,
    val errorMessage: String? = null
)
