package com.example.trackme.data.repository

import com.example.trackme.core.TimeProvider
import com.example.trackme.core.security.DeviceKeyMaterialGenerator
import com.example.trackme.data.local.dao.EnrollmentDao
import com.example.trackme.data.local.entity.EnrollmentEntity
import com.example.trackme.data.network.PairingCompleteRequestDto
import com.example.trackme.data.network.RecoveryApi
import com.example.trackme.domain.model.EnrollmentRequest
import com.example.trackme.domain.model.EnrollmentStatus
import com.example.trackme.domain.model.EnrollmentAuthorizationRole
import com.example.trackme.domain.model.OwnershipType
import com.example.trackme.domain.model.PairingMethod
import com.example.trackme.domain.model.RegistrationState
import com.example.trackme.domain.repository.EnrollmentRepository
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withTimeoutOrNull

@Singleton
class EnrollmentRepositoryImpl @Inject constructor(
    private val enrollmentDao: EnrollmentDao,
    private val recoveryApi: RecoveryApi,
    private val deviceKeyMaterialGenerator: DeviceKeyMaterialGenerator,
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

    override suspend fun enroll(request: EnrollmentRequest): EnrollmentStatus {
        val keyMaterial = deviceKeyMaterialGenerator.generateOrLoad(
            aliasSeed = "${request.organizationName}:${request.deviceAlias}:${request.pairingCredential}"
        )
        val backendBinding = withTimeoutOrNull(BACKEND_ENROLLMENT_TIMEOUT_MS) {
            runCatching {
                recoveryApi.completePairing(
                    PairingCompleteRequestDto(
                        token = request.pairingCredential.takeUnless { request.pairingMethod == PairingMethod.QR_CODE_URI },
                        qrPayload = request.pairingCredential.takeIf { request.pairingMethod == PairingMethod.QR_CODE_URI },
                        alias = request.deviceAlias,
                        ownerSubject = request.ownerSubject,
                        keyId = keyMaterial.keyId,
                        publicKeyPem = keyMaterial.publicKeyPem,
                        algorithm = keyMaterial.algorithm
                    )
                )
            }.getOrNull()
        }

        val entity = EnrollmentEntity(
            isEnrolled = true,
            organizationName = request.organizationName,
            consentVersion = request.consentVersion,
            enrolledAtEpochMs = timeProvider.nowEpochMillis(),
            deviceAlias = request.deviceAlias,
            orgId = backendBinding?.orgId,
            deviceId = backendBinding?.deviceId,
            ownershipBindingId = backendBinding?.ownershipBindingId,
            ownerSubject = backendBinding?.ownerSubject ?: request.ownerSubject,
            ownershipType = request.ownershipType.name,
            authorizationRole = request.authorizationRole.name,
            pairingMethod = request.pairingMethod.name,
            keyId = keyMaterial.keyId,
            keyAlgorithm = keyMaterial.algorithm,
            registrationState = if (backendBinding != null) {
                RegistrationState.VERIFIED.name
            } else {
                RegistrationState.PENDING_BACKEND_VERIFICATION.name
            }
        )
        enrollmentDao.upsert(entity)
        return entity.toDomain()
    }

    private fun EnrollmentEntity.toDomain(): EnrollmentStatus {
        return EnrollmentStatus(
            isEnrolled = isEnrolled,
            organizationName = organizationName,
            consentVersion = consentVersion,
            enrolledAtEpochMs = enrolledAtEpochMs,
            deviceAlias = deviceAlias,
            orgId = orgId,
            deviceId = deviceId,
            ownershipBindingId = ownershipBindingId,
            ownerSubject = ownerSubject,
            ownershipType = ownershipType?.toEnumOrNull<OwnershipType>(),
            authorizationRole = authorizationRole?.toEnumOrNull<EnrollmentAuthorizationRole>(),
            pairingMethod = pairingMethod?.toEnumOrNull<PairingMethod>(),
            keyId = keyId,
            keyAlgorithm = keyAlgorithm,
            registrationState = registrationState?.toEnumOrNull<RegistrationState>()
                ?: RegistrationState.PENDING_BACKEND_VERIFICATION
        )
    }

    private inline fun <reified T : Enum<T>> String.toEnumOrNull(): T? {
        return enumValues<T>().firstOrNull { it.name == this }
    }

    private companion object {
        const val BACKEND_ENROLLMENT_TIMEOUT_MS = 8_000L
    }
}
