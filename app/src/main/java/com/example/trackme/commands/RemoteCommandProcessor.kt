package com.example.trackme.commands

import com.example.trackme.core.TimeProvider
import com.example.trackme.domain.model.DeviceCommand
import com.example.trackme.domain.model.DeviceCommandStatus
import com.example.trackme.domain.model.DeviceCommandType
import com.example.trackme.domain.repository.AuditRepository
import com.example.trackme.domain.repository.CommandRepository
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

interface PendingCommandProcessor {
    suspend fun processPendingCommands()
}

@Singleton
class RemoteCommandProcessor @Inject constructor(
    private val commandRepository: CommandRepository,
    private val commandSignatureVerifier: CommandSignatureVerifier,
    private val lostModeCommandExecutor: LostModeCommandExecutor,
    private val recoveryMessageNotifier: RecoveryMessageNotifier,
    private val deviceAdminCommandController: DeviceAdminCommandController,
    private val auditRepository: AuditRepository,
    private val json: Json,
    private val timeProvider: TimeProvider,
) : PendingCommandProcessor {

    override suspend fun processPendingCommands() {
        commandRepository.getOpenCommands().forEach { command ->
            process(command)
        }
    }

    suspend fun process(command: DeviceCommand) {
        if (!commandSignatureVerifier.verify(command.payloadJson, command.signature, command.signatureAlgorithm)) {
            fail(command, "Command signature verification failed.")
            return
        }
        if (command.expiresAtEpochMs != null && command.expiresAtEpochMs <= timeProvider.nowEpochMillis()) {
            expire(command, "Command expired before the device processed it.")
            return
        }
        if (command.status == DeviceCommandStatus.PENDING || command.status == DeviceCommandStatus.SENT) {
            commandRepository.updateLocalStatus(command.commandId, DeviceCommandStatus.DELIVERED)
        }
        when (command.type) {
            DeviceCommandType.ENTER_LOST_MODE -> executeLostMode(command)
            DeviceCommandType.DISPLAY_RECOVERY_MESSAGE -> executeDisplayRecoveryMessage(command)
            DeviceCommandType.LOCK -> executePolicyAction(command, isWipe = false)
            DeviceCommandType.WIPE -> executePolicyAction(command, isWipe = true)
        }
    }

    private suspend fun executeLostMode(command: DeviceCommand) {
        val payload = json.parseToJsonElement(command.payloadJson).jsonObject
        val untilEpochMs = payload["lost_mode_until"]?.jsonPrimitive?.content?.let { java.time.Instant.parse(it).toEpochMilli() }
            ?: run {
                fail(command, "Lost mode command was missing a lost_mode_until timestamp.")
                return
            }
        runCatching {
            lostModeCommandExecutor.enable(untilEpochMs)
            auditRepository.appendEvent(
                type = "COMMAND_ENTER_LOST_MODE_EXECUTED",
                summary = "Remote lost mode command executed",
                metadata = mapOf(
                    "commandId" to command.commandId,
                    "reason" to command.reason,
                    "untilEpochMs" to untilEpochMs.toString(),
                )
            )
        }.fold(
            onSuccess = {
                commandRepository.acknowledgeCommand(command.commandId, DeviceCommandStatus.ACKED, metadata = executedMetadata())
            },
            onFailure = { fail(command, it.message ?: "Unable to enable lost mode.") }
        )
    }

    private suspend fun executeDisplayRecoveryMessage(command: DeviceCommand) {
        val payload = json.parseToJsonElement(command.payloadJson).jsonObject
        val message = payload["recovery_message"]?.jsonPrimitive?.content
        if (message.isNullOrBlank()) {
            fail(command, "Recovery message command did not include message text.")
            return
        }
        recoveryMessageNotifier.showRecoveryMessage(message, command.reason).fold(
            onSuccess = {
                auditRepository.appendEvent(
                    type = "COMMAND_DISPLAY_RECOVERY_MESSAGE_EXECUTED",
                    summary = "Visible recovery message displayed",
                    metadata = mapOf(
                        "commandId" to command.commandId,
                        "reason" to command.reason,
                    )
                )
                commandRepository.acknowledgeCommand(command.commandId, DeviceCommandStatus.ACKED, metadata = executedMetadata())
            },
            onFailure = { fail(command, it.message ?: "Unable to show recovery message notification.") }
        )
    }

    private suspend fun executePolicyAction(command: DeviceCommand, isWipe: Boolean) {
        val actionResult = if (isWipe) {
            deviceAdminCommandController.wipeDevice()
        } else {
            deviceAdminCommandController.lockDevice()
        }
        actionResult.fold(
            onSuccess = {
                val eventType = if (isWipe) "COMMAND_WIPE_EXECUTED" else "COMMAND_LOCK_EXECUTED"
                auditRepository.appendEvent(
                    type = eventType,
                    summary = "Policy-managed remote command executed",
                    metadata = mapOf(
                        "commandId" to command.commandId,
                        "reason" to command.reason,
                    )
                )
                commandRepository.acknowledgeCommand(command.commandId, DeviceCommandStatus.ACKED, metadata = executedMetadata())
            },
            onFailure = { fail(command, it.message ?: "Policy-managed command failed.") }
        )
    }

    private suspend fun expire(command: DeviceCommand, reason: String) {
        auditRepository.appendEvent(
            type = "COMMAND_EXPIRED",
            summary = "Remote command expired before execution",
            metadata = mapOf("commandId" to command.commandId, "reason" to reason)
        )
        commandRepository.acknowledgeCommand(command.commandId, DeviceCommandStatus.EXPIRED, lastError = reason)
    }

    private suspend fun fail(command: DeviceCommand, reason: String) {
        auditRepository.appendEvent(
            type = "COMMAND_FAILED",
            summary = "Remote command processing failed",
            metadata = mapOf("commandId" to command.commandId, "reason" to reason)
        )
        commandRepository.acknowledgeCommand(command.commandId, DeviceCommandStatus.FAILED, lastError = reason)
    }

    private fun executedMetadata(): Map<String, String> {
        return mapOf("executedAtEpochMs" to timeProvider.nowEpochMillis().toString())
    }
}
