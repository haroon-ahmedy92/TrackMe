package com.example.trackme.data.repository

import com.example.trackme.core.TimeProvider
import com.example.trackme.data.local.dao.EnrollmentDao
import com.example.trackme.data.local.dao.TelemetryQueueDao
import com.example.trackme.data.local.entity.EnrollmentEntity
import com.example.trackme.data.local.entity.TelemetryQueueEntity
import com.example.trackme.data.network.CommandAckRequestDto
import com.example.trackme.data.network.CommandEnvelopeDto
import com.example.trackme.data.network.ConfirmStolenRequestDto
import com.example.trackme.data.network.DeviceCommandSyncRequestDto
import com.example.trackme.data.network.DevicePushTokenRegistrationRequestDto
import com.example.trackme.data.network.IncidentRecordResponseDto
import com.example.trackme.data.network.IncidentRemoteActionResponseDto
import com.example.trackme.data.network.IncidentResolutionRequestDto
import com.example.trackme.data.network.IncidentTimelineEventDto
import com.example.trackme.data.network.LocationIngestBatchRequestDto
import com.example.trackme.data.network.LocationIngestBatchResponseDto
import com.example.trackme.data.network.LocationIngestBatchItemResultDto
import com.example.trackme.data.network.MarkDeviceLostRequestDto
import com.example.trackme.data.network.OwnershipBindingResponseDto
import com.example.trackme.data.network.PairingCompleteRequestDto
import com.example.trackme.data.network.PlatformLocationIngestRequestDto
import com.example.trackme.data.network.RecoveryApi
import com.example.trackme.data.network.RemoteLockDecisionRequestDto
import com.example.trackme.data.network.RemoteWipeDecisionRequestDto
import com.example.trackme.domain.model.NetworkType
import com.example.trackme.location.NetworkContext
import com.example.trackme.location.NetworkContextCollector
import com.example.trackme.telemetry.GzipTelemetryCompressionCodec
import com.example.trackme.telemetry.TelemetryRetryPolicy
import com.example.trackme.telemetry.TelemetrySyncPolicy
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test

class TelemetrySyncRepositoryImplTest {

    @Test
    fun enqueue_and_sync_marksRowsUploaded() = runTest {
        val queueDao = FakeTelemetryQueueDao()
        val api = FakeTelemetryRecoveryApi()
        val repository = TelemetrySyncRepositoryImpl(
            telemetryQueueDao = queueDao,
            enrollmentDao = FakeVerifiedEnrollmentDao(),
            recoveryApi = api,
            json = Json { explicitNulls = false },
            networkContextCollector = FakeNetworkContextCollector(NetworkType.WIFI),
            compressionCodec = GzipTelemetryCompressionCodec(),
            retryPolicy = TelemetryRetryPolicy(),
            syncPolicy = TelemetrySyncPolicy(),
            timeProvider = FakeTelemetryTimeProvider(),
        )

        repository.enqueue(request(idempotencyKey = "loc-1"))
        repository.syncPending()

        assertEquals(0, repository.pendingCount())
        assertEquals(1, api.requests.size)
        assertEquals("loc-1", api.requests.single().items.single().idempotencyKey)
        assertNotNull(queueDao.rows.single().uploadedAtEpochMs)
    }

    @Test
    fun syncPending_onFailureSchedulesRetry() = runTest {
        val queueDao = FakeTelemetryQueueDao()
        val api = FakeTelemetryRecoveryApi(shouldFail = true)
        val repository = TelemetrySyncRepositoryImpl(
            telemetryQueueDao = queueDao,
            enrollmentDao = FakeVerifiedEnrollmentDao(),
            recoveryApi = api,
            json = Json { explicitNulls = false },
            networkContextCollector = FakeNetworkContextCollector(NetworkType.CELLULAR),
            compressionCodec = GzipTelemetryCompressionCodec(),
            retryPolicy = TelemetryRetryPolicy(),
            syncPolicy = TelemetrySyncPolicy(),
            timeProvider = FakeTelemetryTimeProvider(),
        )
        repository.enqueue(request(idempotencyKey = "loc-2"))

        runCatching { repository.syncPending() }

        val row = queueDao.rows.single()
        assertEquals(1, row.attemptCount)
        assertEquals("simulated failure", row.lastError)
    }
}

private fun request(idempotencyKey: String): PlatformLocationIngestRequestDto {
    return PlatformLocationIngestRequestDto(
        orgId = "org-1",
        deviceId = "device-1",
        mode = "normal",
        idempotencyKey = idempotencyKey,
        capturedAt = "2026-03-14T12:00:00Z",
        capturedAtEpochMs = 1_710_000_000_000L,
        latitude = -6.7924,
        longitude = 39.2083,
        accuracyMeters = 18f,
        precision = "moderate",
        confidenceScore = 76,
        sourceMethods = listOf("fused_last_known"),
        networkType = "wifi",
        batteryPercent = 81,
        motionState = "still",
        telemetrySignature = "abc123",
        telemetryKeyId = "device-key-1",
        telemetryPayloadHash = "a".repeat(64),
        integrityVerdict = "trusted",
    )
}

private class FakeVerifiedEnrollmentDao : EnrollmentDao {
    private val state = MutableStateFlow(
        EnrollmentEntity(
            isEnrolled = true,
            organizationName = "Acme",
            consentVersion = "2026-03-14",
            enrolledAtEpochMs = 1_710_000_000_000L,
            deviceAlias = "Field Phone",
            orgId = "org-1",
            deviceId = "device-1",
            ownershipBindingId = "binding-1",
            ownerSubject = "owner@example.com",
            ownershipType = "SINGLE_USER",
            authorizationRole = "OWNER",
            pairingMethod = "ENROLLMENT_TOKEN",
            keyId = "device-key-1",
            keyAlgorithm = "SHA256withECDSA",
            keyHardwareBacked = false,
            keyAttestationFormat = "android_keystore_x509_chain",
            registrationState = "VERIFIED",
        )
    )

    override fun observeById(id: Int): Flow<EnrollmentEntity?> = state

    override suspend fun upsert(entity: EnrollmentEntity) {
        state.value = entity
    }
}

private class FakeTelemetryQueueDao : TelemetryQueueDao {
    val rows = mutableListOf<TelemetryQueueEntity>()

    override suspend fun insert(entity: TelemetryQueueEntity): Long {
        if (rows.none { it.idempotencyKey == entity.idempotencyKey }) {
            rows += entity
            return 1L
        }
        return -1L
    }

    override suspend fun getDue(limit: Int, nowEpochMs: Long): List<TelemetryQueueEntity> {
        return rows
            .filter { it.uploadedAtEpochMs == null && it.nextRetryAtEpochMs <= nowEpochMs }
            .sortedBy { it.createdAtEpochMs }
            .take(limit)
    }

    override suspend fun markUploaded(idempotencyKey: String, uploadedAtEpochMs: Long) {
        replace(idempotencyKey) {
            it.copy(uploadedAtEpochMs = uploadedAtEpochMs, lastAttemptAtEpochMs = uploadedAtEpochMs, lastError = null)
        }
    }

    override suspend fun markRetry(
        idempotencyKey: String,
        attemptCount: Int,
        nextRetryAtEpochMs: Long,
        lastAttemptAtEpochMs: Long,
        lastError: String,
    ) {
        replace(idempotencyKey) {
            it.copy(
                attemptCount = attemptCount,
                nextRetryAtEpochMs = nextRetryAtEpochMs,
                lastAttemptAtEpochMs = lastAttemptAtEpochMs,
                lastError = lastError,
            )
        }
    }

    override suspend fun countPending(): Int = rows.count { it.uploadedAtEpochMs == null }

    private fun replace(idempotencyKey: String, transform: (TelemetryQueueEntity) -> TelemetryQueueEntity) {
        val index = rows.indexOfFirst { it.idempotencyKey == idempotencyKey }
        rows[index] = transform(rows[index])
    }
}

private class FakeNetworkContextCollector(
    private val networkType: NetworkType,
) : NetworkContextCollector {
    override fun collect(): NetworkContext = NetworkContext(networkType = networkType)
}

private class FakeTelemetryTimeProvider : TimeProvider {
    override fun nowEpochMillis(): Long = 1_710_000_000_000L
}

private class FakeTelemetryRecoveryApi(
    private val shouldFail: Boolean = false,
) : RecoveryApi {
    val requests = mutableListOf<LocationIngestBatchRequestDto>()

    override suspend fun submitCheckIn(request: com.example.trackme.data.network.CheckInRequest) = Unit

    override suspend fun ingestLocationsBatch(request: LocationIngestBatchRequestDto): LocationIngestBatchResponseDto {
        if (shouldFail) error("simulated failure")
        requests += request
        return LocationIngestBatchResponseDto(
            acceptedCount = request.items.size,
            duplicateCount = 0,
            failedCount = 0,
            results = request.items.map {
                LocationIngestBatchItemResultDto(
                    idempotencyKey = it.idempotencyKey,
                    eventId = "event-${it.idempotencyKey}",
                    accepted = true,
                    duplicate = false,
                )
            }
        )
    }

    override suspend fun submitAuditEvent(request: com.example.trackme.data.network.AuditEventRequest) = Unit

    override suspend fun completePairing(request: PairingCompleteRequestDto): OwnershipBindingResponseDto {
        error("Not needed in this test")
    }

    override suspend fun registerDevicePushToken(request: DevicePushTokenRegistrationRequestDto) = Unit

    override suspend fun syncPendingCommands(request: DeviceCommandSyncRequestDto): List<CommandEnvelopeDto> = emptyList()

    override suspend fun acknowledgeCommand(commandId: String, request: CommandAckRequestDto) = Unit

    override suspend fun markDeviceLost(request: MarkDeviceLostRequestDto): IncidentRecordResponseDto {
        error("Not needed in this test")
    }

    override suspend fun confirmStolen(
        incidentId: String,
        request: ConfirmStolenRequestDto,
    ): IncidentRecordResponseDto = error("Not needed in this test")

    override suspend fun requestRemoteLockDecision(
        incidentId: String,
        request: RemoteLockDecisionRequestDto,
    ): IncidentRemoteActionResponseDto = error("Not needed in this test")

    override suspend fun requestRemoteWipeDecision(
        incidentId: String,
        request: RemoteWipeDecisionRequestDto,
    ): IncidentRemoteActionResponseDto = error("Not needed in this test")

    override suspend fun markRecovered(
        incidentId: String,
        request: IncidentResolutionRequestDto,
    ): IncidentRecordResponseDto = error("Not needed in this test")

    override suspend fun cancelIncident(
        incidentId: String,
        request: IncidentResolutionRequestDto,
    ): IncidentRecordResponseDto = error("Not needed in this test")

    override suspend fun decommissionDevice(
        incidentId: String,
        request: IncidentResolutionRequestDto,
    ): IncidentRecordResponseDto = error("Not needed in this test")

    override suspend fun getIncidentTimeline(incidentId: String): List<IncidentTimelineEventDto> {
        error("Not needed in this test")
    }
}
