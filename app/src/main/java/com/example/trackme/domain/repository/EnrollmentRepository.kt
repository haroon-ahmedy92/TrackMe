package com.example.trackme.domain.repository

import com.example.trackme.domain.model.EnrollmentStatus
import kotlinx.coroutines.flow.Flow

interface EnrollmentRepository {
    fun observeEnrollmentStatus(): Flow<EnrollmentStatus>
    suspend fun enroll(organizationName: String, consentVersion: String)
}
