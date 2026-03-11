package com.example.trackme.data.repository

import com.example.trackme.core.TimeProvider
import com.example.trackme.data.local.dao.EnrollmentDao
import com.example.trackme.data.local.entity.EnrollmentEntity
import com.example.trackme.domain.model.EnrollmentStatus
import com.example.trackme.domain.repository.EnrollmentRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class EnrollmentRepositoryImpl @Inject constructor(
    private val enrollmentDao: EnrollmentDao,
    private val timeProvider: TimeProvider
) : EnrollmentRepository {

    override fun observeEnrollmentStatus(): Flow<EnrollmentStatus> {
        return enrollmentDao.observeById().map { entity ->
            entity?.toDomain() ?: EnrollmentStatus(
                isEnrolled = false,
                organizationName = null,
                consentVersion = null,
                enrolledAtEpochMs = null
            )
        }
    }

    override suspend fun enroll(organizationName: String, consentVersion: String) {
        enrollmentDao.upsert(
            EnrollmentEntity(
                isEnrolled = true,
                organizationName = organizationName,
                consentVersion = consentVersion,
                enrolledAtEpochMs = timeProvider.nowEpochMillis()
            )
        )
    }

    private fun EnrollmentEntity.toDomain(): EnrollmentStatus {
        return EnrollmentStatus(
            isEnrolled = isEnrolled,
            organizationName = organizationName,
            consentVersion = consentVersion,
            enrolledAtEpochMs = enrolledAtEpochMs
        )
    }
}
