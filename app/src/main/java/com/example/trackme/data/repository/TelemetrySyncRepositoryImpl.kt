package com.example.trackme.data.repository

import com.example.trackme.data.local.dao.EnrollmentDao
import com.example.trackme.data.local.dao.TelemetryQueueDao
import com.example.trackme.data.local.entity.EnrollmentEntity
import com.example.trackme.data.local.entity.TelemetryQueueEntity
import com.example.trackme.data.network.LocationIngestBatchRequestDto
import com.example.trackme.data.network.PlatformLocationIngestRequestDto
import com.example.trackme.data.network.RecoveryApi
import com.example.trackme.domain.model.CheckInMode
import com.example.trackme.domain.model.RegistrationState
import com.example.trackme.domain.repository.TelemetrySyncRepository
import com.example.trackme.location.NetworkContextCollector
import com.example.trackme.telemetry.TelemetryCompressionCodec
import com.example.trackme.telemetry.TelemetryRetryPolicy
import com.example.trackme.telemetry.TelemetrySyncPolicy
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.serialization.json.Json

@Singleton
class TelemetrySyncRepositoryImpl @Inject constructor(
    private val telemetryQueueDao: TelemetryQueueDao,
    private val enrollmentDao: EnrollmentDao,
    private val recoveryApi: RecoveryApi,
    private val json: Json,
    private val networkContextCollector: NetworkContextCollector,
    private val compressionCodec: TelemetryCompressionCodec,
    private val retryPolicy: TelemetryRetryPolicy,
    private val syncPolicy: TelemetrySyncPolicy,
    private val timeProvider: com.example.trackme.core.TimeProvider,
) : TelemetrySyncRepository {

    override suspend fun enqueue(request: PlatformLocationIngestRequestDto) {
        val now = timeProvider.nowEpochMillis()
        val payloadJson = json.encodeToString(PlatformLocationIngestRequestDto.serializer(), request)
        telemetryQueueDao.insert(
            TelemetryQueueEntity(
                idempotencyKey = request.idempotencyKey,
                orgId = request.orgId,
                deviceId = request.deviceId,
                mode = request.mode,
                capturedAtEpochMs = request.capturedAtEpochMs,
                createdAtEpochMs = now,
                compressionAlgorithm = compressionCodec.algorithm,
                payloadCompressed = compressionCodec.compress(payloadJson),
                payloadSizeBytes = payloadJson.toByteArray(Charsets.UTF_8).size,
                networkType = request.networkType ?: "unknown",
                nextRetryAtEpochMs = now,
            )
        )
    }

    override suspend fun syncPending() {
        val enrollment = enrollmentDao.observeById().firstOrNullTelemetryIdentity() ?: return
        val now = timeProvider.nowEpochMillis()
        val preview = telemetryQueueDao.getDue(limit = PREVIEW_BATCH_LIMIT, nowEpochMs = now)
            .filter { it.orgId == enrollment.orgId && it.deviceId == enrollment.deviceId }
        if (preview.isEmpty()) return

        val modes = preview.map { it.mode.toCheckInMode() }
        val policy = syncPolicy.resolve(networkContextCollector.collect().networkType, modes)
        if (!policy.shouldSync) return

        val dueRows = telemetryQueueDao.getDue(limit = policy.maxBatchSize, nowEpochMs = now)
            .filter { it.orgId == enrollment.orgId && it.deviceId == enrollment.deviceId }
        if (dueRows.isEmpty()) return

        val requests = dueRows.map { row ->
            val payloadJson = compressionCodec.decompress(row.payloadCompressed)
            json.decodeFromString(PlatformLocationIngestRequestDto.serializer(), payloadJson)
        }

        runCatching {
            recoveryApi.ingestLocationsBatch(
                LocationIngestBatchRequestDto(items = requests)
            )
        }.onSuccess { response ->
            val resultsByKey = response.results.associateBy { it.idempotencyKey }
            dueRows.forEach { row ->
                val result = resultsByKey[row.idempotencyKey]
                if (result == null || result.accepted || result.duplicate) {
                    telemetryQueueDao.markUploaded(row.idempotencyKey, now)
                } else {
                    val attemptCount = row.attemptCount + 1
                    telemetryQueueDao.markRetry(
                        idempotencyKey = row.idempotencyKey,
                        attemptCount = attemptCount,
                        nextRetryAtEpochMs = retryPolicy.nextRetryEpochMs(now, attemptCount),
                        lastAttemptAtEpochMs = now,
                        lastError = result.error ?: "upload_rejected",
                    )
                }
            }
        }.onFailure { throwable ->
            dueRows.forEach { row ->
                val attemptCount = row.attemptCount + 1
                telemetryQueueDao.markRetry(
                    idempotencyKey = row.idempotencyKey,
                    attemptCount = attemptCount,
                    nextRetryAtEpochMs = retryPolicy.nextRetryEpochMs(now, attemptCount),
                    lastAttemptAtEpochMs = now,
                    lastError = throwable.message ?: "network_error",
                )
            }
            throw throwable
        }
    }

    override suspend fun pendingCount(): Int = telemetryQueueDao.countPending()

    private fun String.toCheckInMode(): CheckInMode {
        return runCatching { CheckInMode.valueOf(this) }.getOrDefault(CheckInMode.NORMAL)
    }

    private companion object {
        const val PREVIEW_BATCH_LIMIT = 25
    }
}

private data class TelemetryEnrollmentIdentity(
    val orgId: String,
    val deviceId: String,
    val keyId: String,
)

private suspend fun Flow<EnrollmentEntity?>.firstOrNullTelemetryIdentity(): TelemetryEnrollmentIdentity? {
    return first()?.takeIf {
        it.isEnrolled &&
            !it.orgId.isNullOrBlank() &&
            !it.deviceId.isNullOrBlank() &&
            !it.keyId.isNullOrBlank() &&
            it.registrationState == RegistrationState.VERIFIED.name
    }?.let {
        TelemetryEnrollmentIdentity(
            orgId = requireNotNull(it.orgId),
            deviceId = requireNotNull(it.deviceId),
            keyId = requireNotNull(it.keyId),
        )
    }
}
