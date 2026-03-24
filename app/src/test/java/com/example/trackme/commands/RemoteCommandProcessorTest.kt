package com.example.trackme.commands

import com.example.trackme.core.TimeProvider
import com.example.trackme.domain.model.AuditEvent
import com.example.trackme.domain.model.DeviceCommand
import com.example.trackme.domain.model.DeviceCommandStatus
import com.example.trackme.domain.model.DeviceCommandType
import com.example.trackme.domain.repository.AuditRepository
import com.example.trackme.domain.repository.CommandRepository
import java.time.Instant
import java.security.KeyPairGenerator
import java.security.Signature
import java.util.Base64
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class RemoteCommandProcessorTest {

    private val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
    }
    private val timeProvider = object : TimeProvider {
        override fun nowEpochMillis(): Long = 1_710_410_000_000
    }
    private val keyPair = KeyPairGenerator.getInstance("EC").apply {
        initialize(256)
    }.generateKeyPair()
    private val verifier = CommandSignatureVerifier(
        json = json,
        configuredPublicKeyPem = keyPair.public.toPem(),
        forTests = true,
    )

    @Test
    fun process_displayRecoveryMessage_marksDeliveredAndAcked() = runTest {
        val repository = RecordingCommandRepository()
        val notifier = RecordingRecoveryNotifier(Result.success(Unit))
        val auditRepository = RecordingAuditRepository()
        val processor = RemoteCommandProcessor(
            commandRepository = repository,
            commandSignatureVerifier = verifier,
            lostModeCommandExecutor = RecordingLostModeExecutor(),
            recoveryMessageNotifier = notifier,
            deviceAdminCommandController = RecordingDeviceAdminController(),
            auditRepository = auditRepository,
            json = json,
            timeProvider = timeProvider,
        )
        val payloadJson = """{"action_kind":"display_recovery_message","recovery_message":"Please return this device to TrackMe support.","requested_at":"2026-03-14T10:00:00Z"}"""
        val command = buildCommand(payloadJson = payloadJson, signature = sign(payloadJson))

        processor.process(command)

        assertEquals(listOf(DeviceCommandStatus.DELIVERED), repository.localStatuses)
        assertEquals(DeviceCommandStatus.ACKED, repository.acknowledgedStatus)
        assertTrue(notifier.messages.single().contains("Please return this device"))
        assertEquals("COMMAND_DISPLAY_RECOVERY_MESSAGE_EXECUTED", auditRepository.events.single().first)
    }

    @Test
    fun process_expiredCommand_marksExpiredWithoutExecution() = runTest {
        val repository = RecordingCommandRepository()
        val notifier = RecordingRecoveryNotifier(Result.success(Unit))
        val auditRepository = RecordingAuditRepository()
        val processor = RemoteCommandProcessor(
            commandRepository = repository,
            commandSignatureVerifier = verifier,
            lostModeCommandExecutor = RecordingLostModeExecutor(),
            recoveryMessageNotifier = notifier,
            deviceAdminCommandController = RecordingDeviceAdminController(),
            auditRepository = auditRepository,
            json = json,
            timeProvider = timeProvider,
        )
        val payloadJson = """{"action_kind":"display_recovery_message","recovery_message":"Expired command","requested_at":"2026-03-14T10:00:00Z"}"""
        val command = buildCommand(
            payloadJson = payloadJson,
            signature = sign(payloadJson),
            expiresAtEpochMs = Instant.parse("2024-01-01T00:00:00Z").toEpochMilli(),
        )

        processor.process(command)

        assertEquals(DeviceCommandStatus.EXPIRED, repository.acknowledgedStatus)
        assertTrue(notifier.messages.isEmpty())
        assertEquals("COMMAND_EXPIRED", auditRepository.events.single().first)
    }

    private fun buildCommand(
        payloadJson: String,
        signature: String,
        expiresAtEpochMs: Long? = Instant.parse("2027-01-01T00:00:00Z").toEpochMilli(),
    ): DeviceCommand {
        return DeviceCommand(
            commandId = "cmd-1",
            orgId = "org-1",
            deviceId = "device-1",
            incidentId = "incident-1",
            type = DeviceCommandType.DISPLAY_RECOVERY_MESSAGE,
            status = DeviceCommandStatus.PENDING,
            reason = "Owner requested visible recovery assistance.",
            payloadJson = payloadJson,
            signature = signature,
            signatureAlgorithm = CommandSignatureVerifier.SUPPORTED_ALGORITHM,
            requestedBy = "admin@example.com",
            requestedAtEpochMs = Instant.parse("2026-03-14T10:00:00Z").toEpochMilli(),
            expiresAtEpochMs = expiresAtEpochMs,
        )
    }

    private fun sign(payloadJson: String): String {
        val signature = Signature.getInstance("SHA256withECDSA").apply {
            initSign(keyPair.private)
            update(payloadJson.encodeToByteArray())
        }.sign()
        return Base64.getEncoder().encodeToString(signature)
    }

    private fun java.security.PublicKey.toPem(): String {
        val base64 = Base64.getEncoder().encodeToString(encoded)
        return buildString {
            appendLine("-----BEGIN PUBLIC KEY-----")
            base64.chunked(64).forEach(::appendLine)
            append("-----END PUBLIC KEY-----")
        }
    }
}

private class RecordingCommandRepository : CommandRepository {
    val localStatuses = mutableListOf<DeviceCommandStatus>()
    var acknowledgedStatus: DeviceCommandStatus? = null

    override fun observeCommands(): Flow<List<DeviceCommand>> = flowOf(emptyList())

    override suspend fun registerPushToken(pushToken: String, appVersion: String?) = Unit

    override suspend fun syncPendingCommands() = Unit

    override suspend fun flushPendingAcknowledgements() = Unit

    override suspend fun getOpenCommands(): List<DeviceCommand> = emptyList()

    override suspend fun updateLocalStatus(commandId: String, status: DeviceCommandStatus, lastError: String?) {
        localStatuses += status
    }

    override suspend fun acknowledgeCommand(
        commandId: String,
        status: DeviceCommandStatus,
        lastError: String?,
        metadata: Map<String, String>
    ) {
        acknowledgedStatus = status
    }
}

private class RecordingRecoveryNotifier(
    private val result: Result<Unit>
) : RecoveryMessageNotifier {
    val messages = mutableListOf<String>()

    override fun showRecoveryMessage(message: String, reason: String): Result<Unit> {
        messages += "$message|$reason"
        return result
    }

    override fun showCommandUpdate(title: String, body: String): Result<Unit> {
        messages += "$title|$body"
        return result
    }
}

private class RecordingLostModeExecutor : LostModeCommandExecutor {
    override suspend fun enable(untilEpochMs: Long) = Unit
}

private class RecordingDeviceAdminController : DeviceAdminCommandController {
    override fun lockDevice(): Result<Unit> = Result.success(Unit)
    override fun wipeDevice(): Result<Unit> = Result.success(Unit)
}

private class RecordingAuditRepository : AuditRepository {
    val events = mutableListOf<Pair<String, String>>()

    override fun observeRecentEvents(limit: Int): Flow<List<AuditEvent>> = flowOf(emptyList())

    override suspend fun appendEvent(type: String, summary: String, metadata: Map<String, String>) {
        events += type to summary
    }
}
