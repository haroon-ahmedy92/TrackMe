package com.example.trackme.domain.model

enum class DeviceCommandType {
    ENTER_LOST_MODE,
    DISPLAY_RECOVERY_MESSAGE,
    LOCK,
    WIPE
}

enum class DeviceCommandStatus {
    PENDING,
    SENT,
    DELIVERED,
    ACKED,
    FAILED,
    EXPIRED
}

data class DeviceCommand(
    val commandId: String,
    val orgId: String,
    val deviceId: String,
    val incidentId: String?,
    val type: DeviceCommandType,
    val status: DeviceCommandStatus,
    val reason: String,
    val payloadJson: String,
    val signature: String,
    val signatureAlgorithm: String,
    val requestedBy: String,
    val requestedAtEpochMs: Long,
    val expiresAtEpochMs: Long?,
    val deliveredAtEpochMs: Long? = null,
    val executedAtEpochMs: Long? = null,
    val lastError: String? = null,
    val isServerAcknowledged: Boolean = false
)
