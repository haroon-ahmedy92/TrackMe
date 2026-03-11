package com.example.trackme.domain.model

data class EnrollmentStatus(
    val isEnrolled: Boolean,
    val organizationName: String?,
    val consentVersion: String?,
    val enrolledAtEpochMs: Long?
)
