package com.example.trackme.data.repository

import com.example.trackme.core.TimeProvider
import com.example.trackme.core.security.DeviceKeyMaterial
import com.example.trackme.core.security.DeviceKeyMaterialGenerator
import com.example.trackme.data.local.dao.EnrollmentDao
import com.example.trackme.data.local.entity.EnrollmentEntity
import com.example.trackme.data.network.CommandAckRequestDto
import com.example.trackme.data.network.CommandEnvelopeDto
import com.example.trackme.data.network.ConfirmStolenRequestDto
import com.example.trackme.data.network.DeviceCommandSyncRequestDto
import com.example.trackme.data.network.DevicePushTokenRegistrationRequestDto
import com.example.trackme.data.network.IncidentRecordResponseDto
import com.example.trackme.data.network.IncidentRemoteActionResponseDto
import com.example.trackme.data.network.IncidentResolutionRequestDto
import com.example.trackme.data.network.IncidentTimelineEventDto
import com.example.trackme.data.network.MarkDeviceLostRequestDto
import com.example.trackme.data.network.OwnershipBindingResponseDto
import com.example.trackme.data.network.PairingCompleteRequestDto
import com.example.trackme.data.network.RecoveryApi
import com.example.trackme.data.network.RemoteLockDecisionRequestDto
import com.example.trackme.data.network.RemoteWipeDecisionRequestDto
import com.example.trackme.domain.model.EnrollmentAuthorizationRole
import com.example.trackme.domain.model.EnrollmentRequest
import com.example.trackme.domain.model.OwnershipType
import com.example.trackme.domain.model.PairingMethod
import com.example.trackme.domain.model.RegistrationState
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

class EnrollmentRepositoryImplTest {

    @Test
    fun enroll_marks_status_verified_when_backend_pairing_succeeds() = runTest {
        val dao = FakeEnrollmentDao()
        val repository = EnrollmentRepositoryImpl(
            enrollmentDao = dao,
            recoveryApi = FakeRecoveryApi(
                binding = OwnershipBindingResponseDto(
                    ownershipBindingId = "binding-1",
                    orgId = "org-1",
                    deviceId = "device-1",
                    ownerSubject = "owner@example.com",
                    ownershipType = "SINGLE_USER",
                    proofKind = "ENROLLMENT_TOKEN",
                    consentVersion = "2026-03-10",
                    consentCapturedAt = "2026-03-10T12:00:00Z",
                    isActive = true,
                    createdAt = "2026-03-10T12:00:00Z"
                )
            ),
            deviceKeyMaterialGenerator = FakeDeviceKeyMaterialGenerator(),
            timeProvider = FakeTimeProvider()
        )

        val status = repository.enroll(
            EnrollmentRequest(
                organizationName = "Acme Corp",
                consentVersion = "2026-03-10",
                deviceAlias = "Field Phone 1",
                ownerSubject = "owner@example.com",
                ownershipType = OwnershipType.SINGLE_USER,
                authorizationRole = EnrollmentAuthorizationRole.OWNER,
                pairingCredential = "token-123",
                pairingMethod = PairingMethod.ENROLLMENT_TOKEN
            )
        )

        assertEquals(RegistrationState.VERIFIED, status.registrationState)
        assertEquals("device-1", status.deviceId)
        assertEquals("trackme-test-key", status.keyId)
        assertEquals("Acme Corp", repository.observeEnrollmentStatus().first().organizationName)
    }

    @Test
    fun enroll_falls_back_to_pending_verification_when_backend_is_unreachable() = runTest {
        val dao = FakeEnrollmentDao()
        val repository = EnrollmentRepositoryImpl(
            enrollmentDao = dao,
            recoveryApi = FakeRecoveryApi(binding = null),
            deviceKeyMaterialGenerator = FakeDeviceKeyMaterialGenerator(),
            timeProvider = FakeTimeProvider()
        )

        val status = repository.enroll(
            EnrollmentRequest(
                organizationName = "Acme Corp",
                consentVersion = "2026-03-10",
                deviceAlias = "Warehouse A5",
                ownerSubject = null,
                ownershipType = OwnershipType.ORGANIZATION_OWNED,
                authorizationRole = EnrollmentAuthorizationRole.ADMIN,
                pairingCredential = "trackme://pair?token=abc123",
                pairingMethod = PairingMethod.QR_CODE_URI
            )
        )

        assertEquals(RegistrationState.PENDING_BACKEND_VERIFICATION, status.registrationState)
        assertEquals(PairingMethod.QR_CODE_URI, status.pairingMethod)
        assertNotNull(dao.state.value)
    }
}

private class FakeEnrollmentDao : EnrollmentDao {
    val state = MutableStateFlow<EnrollmentEntity?>(null)

    override fun observeById(id: Int): Flow<EnrollmentEntity?> = state

    override suspend fun upsert(entity: EnrollmentEntity) {
        state.value = entity
    }
}

private class FakeDeviceKeyMaterialGenerator : DeviceKeyMaterialGenerator {
    override fun generateOrLoad(aliasSeed: String): DeviceKeyMaterial {
        return DeviceKeyMaterial(
            keyId = "trackme-test-key",
            publicKeyPem = "-----BEGIN PUBLIC KEY-----\nTEST\n-----END PUBLIC KEY-----",
            algorithm = "RSA"
        )
    }
}

private class FakeTimeProvider : TimeProvider {
    override fun nowEpochMillis(): Long = 1_710_000_000_000
}

private class FakeRecoveryApi(
    private val binding: OwnershipBindingResponseDto?
) : RecoveryApi {
    override suspend fun submitCheckIn(request: com.example.trackme.data.network.CheckInRequest) = Unit

    override suspend fun submitAuditEvent(request: com.example.trackme.data.network.AuditEventRequest) = Unit

    override suspend fun completePairing(request: PairingCompleteRequestDto): OwnershipBindingResponseDto {
        return binding ?: error("backend unavailable")
    }

    override suspend fun registerDevicePushToken(request: DevicePushTokenRegistrationRequestDto) = Unit

    override suspend fun syncPendingCommands(request: DeviceCommandSyncRequestDto): List<CommandEnvelopeDto> = emptyList()

    override suspend fun acknowledgeCommand(commandId: String, request: CommandAckRequestDto) = Unit

    override suspend fun markDeviceLost(request: MarkDeviceLostRequestDto): IncidentRecordResponseDto {
        error("Not needed in this test")
    }

    override suspend fun confirmStolen(
        incidentId: String,
        request: ConfirmStolenRequestDto
    ): IncidentRecordResponseDto = error("Not needed in this test")

    override suspend fun requestRemoteLockDecision(
        incidentId: String,
        request: RemoteLockDecisionRequestDto
    ): IncidentRemoteActionResponseDto = error("Not needed in this test")

    override suspend fun requestRemoteWipeDecision(
        incidentId: String,
        request: RemoteWipeDecisionRequestDto
    ): IncidentRemoteActionResponseDto = error("Not needed in this test")

    override suspend fun markRecovered(
        incidentId: String,
        request: IncidentResolutionRequestDto
    ): IncidentRecordResponseDto = error("Not needed in this test")

    override suspend fun cancelIncident(
        incidentId: String,
        request: IncidentResolutionRequestDto
    ): IncidentRecordResponseDto = error("Not needed in this test")

    override suspend fun decommissionDevice(
        incidentId: String,
        request: IncidentResolutionRequestDto
    ): IncidentRecordResponseDto = error("Not needed in this test")

    override suspend fun getIncidentTimeline(incidentId: String): List<IncidentTimelineEventDto> {
        error("Not needed in this test")
    }
}
