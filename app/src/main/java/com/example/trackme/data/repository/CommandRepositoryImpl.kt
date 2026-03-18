package com.example.trackme.data.repository

import com.example.trackme.core.TimeProvider
import com.example.trackme.core.TelemetrySigner
import com.example.trackme.data.local.dao.DeviceCommandDao
import com.example.trackme.data.local.dao.EnrollmentDao
import com.example.trackme.data.local.entity.DeviceCommandEntity
import com.example.trackme.data.local.entity.EnrollmentEntity
import com.example.trackme.data.network.CommandAckRequestDto
import com.example.trackme.data.network.CommandEnvelopeDto
import com.example.trackme.data.network.DeviceCommandSyncRequestDto
import com.example.trackme.data.network.DevicePushTokenRegistrationRequestDto
import com.example.trackme.data.network.RecoveryApi
import com.example.trackme.domain.model.DeviceCommand
import com.example.trackme.domain.model.DeviceCommandStatus
import com.example.trackme.domain.model.DeviceCommandType
import com.example.trackme.domain.model.RegistrationState
import com.example.trackme.domain.repository.CommandRepository
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.Serializable
import java.time.Instant

@Singleton
class CommandRepositoryImpl @Inject constructor(
    private val commandDao: DeviceCommandDao,
    private val enrollmentDao: EnrollmentDao,
    private val recoveryApi: RecoveryApi,
    private val json: Json,
    private val timeProvider: TimeProvider,
    private val telemetrySigner: TelemetrySigner,
) : CommandRepository {

    override fun observeCommands(): Flow<List<DeviceCommand>> {
        return commandDao.observeAll().map { rows -> rows.map { it.toDomain() } }
    }

    override suspend fun registerPushToken(pushToken: String, appVersion: String?) {
        val enrollment = enrollmentDao.observeById().firstOrNullEnrolled() ?: return
        recoveryApi.registerDevicePushToken(
            DevicePushTokenRegistrationRequestDto(
                orgId = enrollment.orgId,
                deviceId = enrollment.deviceId,
                keyId = enrollment.keyId,
                pushToken = pushToken,
                appVersion = appVersion,
            )
        )
    }

    override suspend fun syncPendingCommands() {
        val enrollment = enrollmentDao.observeById().firstOrNullEnrolled() ?: return
        val receivedAtEpochMs = timeProvider.nowEpochMillis()
        val commands = recoveryApi.syncPendingCommands(
            DeviceCommandSyncRequestDto(
                orgId = enrollment.orgId,
                deviceId = enrollment.deviceId,
                keyId = enrollment.keyId,
            )
        )
        if (commands.isEmpty()) return
        commandDao.upsertAll(commands.map { it.toEntity(receivedAtEpochMs) })
    }

    override suspend fun flushPendingAcknowledgements() {
        val enrollment = enrollmentDao.observeById().firstOrNullEnrolled() ?: return
        val pending = commandDao.getPendingAcknowledgements(
            listOf(
                DeviceCommandStatus.ACKED.name,
                DeviceCommandStatus.FAILED.name,
                DeviceCommandStatus.EXPIRED.name,
            )
        )
        pending.forEach { command ->
            val signedRequest = signAcknowledgement(
                enrollment = enrollment,
                commandId = command.commandId,
                status = command.status.lowercase(),
                errorMessage = command.lastError,
                metadata = buildMap {
                    command.executedAtEpochMs?.let { put("executedAtEpochMs", it.toString()) }
                    command.deliveredAtEpochMs?.let { put("deliveredAtEpochMs", it.toString()) }
                },
            )
            recoveryApi.acknowledgeCommand(
                commandId = command.commandId,
                request = signedRequest,
            )
            commandDao.updateServerAcknowledged(command.commandId, true)
        }
    }

    override suspend fun getOpenCommands(): List<DeviceCommand> {
        return commandDao.getByStatuses(
            listOf(
                DeviceCommandStatus.PENDING.name,
                DeviceCommandStatus.SENT.name,
                DeviceCommandStatus.DELIVERED.name,
            )
        ).map { it.toDomain() }
    }

    override suspend fun updateLocalStatus(commandId: String, status: DeviceCommandStatus, lastError: String?) {
        val now = timeProvider.nowEpochMillis()
        commandDao.updateStatus(
            commandId = commandId,
            status = status.name,
            lastError = lastError,
            deliveredAtEpochMs = if (status == DeviceCommandStatus.DELIVERED) now else null,
            executedAtEpochMs = if (status in terminalStatuses) now else null,
        )
        if (status in terminalStatuses) {
            commandDao.updateServerAcknowledged(commandId, false)
        }
    }

    override suspend fun acknowledgeCommand(
        commandId: String,
        status: DeviceCommandStatus,
        lastError: String?,
        metadata: Map<String, String>
    ) {
        updateLocalStatus(commandId, status, lastError)
        val enrollment = enrollmentDao.observeById().firstOrNullEnrolled() ?: return
        val request = signAcknowledgement(
            enrollment = enrollment,
            commandId = commandId,
            status = status.name.lowercase(),
            errorMessage = lastError,
            metadata = metadata,
        )
        recoveryApi.acknowledgeCommand(
            commandId = commandId,
            request = request,
        )
        commandDao.updateServerAcknowledged(commandId, true)
    }

    private fun signAcknowledgement(
        enrollment: EnrollmentIdentity,
        commandId: String,
        status: String,
        errorMessage: String?,
        metadata: Map<String, String>,
    ): CommandAckRequestDto {
        val unsignedPayload = SignedCommandAckPayload(
            commandId = commandId,
            orgId = enrollment.orgId,
            deviceId = enrollment.deviceId,
            keyId = enrollment.keyId,
            status = status,
            errorMessage = errorMessage,
            metadata = metadata,
        )
        val signedPayload = telemetrySigner.sign(
            json.encodeToString(SignedCommandAckPayload.serializer(), unsignedPayload),
            enrollment.keyId,
        )
        return CommandAckRequestDto(
            orgId = enrollment.orgId,
            deviceId = enrollment.deviceId,
            keyId = enrollment.keyId,
            status = status,
            errorMessage = errorMessage,
            metadata = metadata,
            telemetrySignature = signedPayload.signature,
            telemetryAlgorithm = signedPayload.algorithm,
            telemetryPayloadHash = signedPayload.payloadHash,
        )
    }

    private fun CommandEnvelopeDto.toEntity(receivedAtEpochMs: Long): DeviceCommandEntity {
        val deliveredAt = if (state.equals(DeviceCommandStatus.DELIVERED.name, ignoreCase = true)) {
            receivedAtEpochMs
        } else {
            null
        }
        return DeviceCommandEntity(
            commandId = remoteActionId,
            orgId = orgId,
            deviceId = deviceId,
            incidentId = incidentId,
            type = actionKind.uppercase(),
            status = state.uppercase(),
            reason = reason,
            payloadJson = json.encodeToString(JsonObject.serializer(), JsonObject(payload.toSortedMap())),
            signature = signature,
            signatureAlgorithm = signatureAlgorithm,
            requestedBy = requestedBySub,
            requestedAtEpochMs = requestedAt.toEpochMillis(),
            expiresAtEpochMs = expiresAt?.toEpochMillis(),
            deliveredAtEpochMs = deliveredAt,
            executedAtEpochMs = null,
            lastError = null,
            isServerAcknowledged = false,
        )
    }

    private fun DeviceCommandEntity.toDomain(): DeviceCommand {
        return DeviceCommand(
            commandId = commandId,
            orgId = orgId,
            deviceId = deviceId,
            incidentId = incidentId,
            type = enumValueOfOrDefault(type, DeviceCommandType.DISPLAY_RECOVERY_MESSAGE),
            status = enumValueOfOrDefault(status, DeviceCommandStatus.PENDING),
            reason = reason,
            payloadJson = payloadJson,
            signature = signature,
            signatureAlgorithm = signatureAlgorithm,
            requestedBy = requestedBy,
            requestedAtEpochMs = requestedAtEpochMs,
            expiresAtEpochMs = expiresAtEpochMs,
            deliveredAtEpochMs = deliveredAtEpochMs,
            executedAtEpochMs = executedAtEpochMs,
            lastError = lastError,
            isServerAcknowledged = isServerAcknowledged,
        )
    }

    private fun String.toEpochMillis(): Long = Instant.parse(this).toEpochMilli()

    private inline fun <reified T : Enum<T>> enumValueOfOrDefault(value: String, default: T): T {
        return enumValues<T>().firstOrNull { it.name == value } ?: default
    }

    private companion object {
        val terminalStatuses = setOf(
            DeviceCommandStatus.ACKED,
            DeviceCommandStatus.FAILED,
            DeviceCommandStatus.EXPIRED,
        )
    }
}

private data class EnrollmentIdentity(
    val orgId: String,
    val deviceId: String,
    val keyId: String,
)

@Serializable
private data class SignedCommandAckPayload(
    val commandId: String,
    val orgId: String,
    val deviceId: String,
    val keyId: String,
    val status: String,
    val errorMessage: String? = null,
    val metadata: Map<String, String> = emptyMap(),
)

private suspend fun Flow<EnrollmentEntity?>.firstOrNullEnrolled(): EnrollmentIdentity? {
    return first()?.takeIf {
        it.isEnrolled &&
            !it.orgId.isNullOrBlank() &&
            !it.deviceId.isNullOrBlank() &&
            !it.keyId.isNullOrBlank() &&
            it.registrationState == RegistrationState.VERIFIED.name
    }?.let {
        EnrollmentIdentity(
            orgId = requireNotNull(it.orgId),
            deviceId = requireNotNull(it.deviceId),
            keyId = requireNotNull(it.keyId),
        )
    }
}
