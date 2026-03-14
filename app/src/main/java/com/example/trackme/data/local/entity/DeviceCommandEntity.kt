package com.example.trackme.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "device_commands")
data class DeviceCommandEntity(
    @PrimaryKey val commandId: String,
    val orgId: String,
    val deviceId: String,
    val incidentId: String?,
    val type: String,
    val status: String,
    val reason: String,
    val payloadJson: String,
    val signature: String,
    val signatureAlgorithm: String,
    val requestedBy: String,
    val requestedAtEpochMs: Long,
    val expiresAtEpochMs: Long?,
    val deliveredAtEpochMs: Long?,
    val executedAtEpochMs: Long?,
    val lastError: String?,
    val isServerAcknowledged: Boolean
)
