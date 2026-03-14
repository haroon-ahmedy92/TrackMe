package com.example.trackme.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "telemetry_queue")
data class TelemetryQueueEntity(
    @PrimaryKey
    @ColumnInfo(name = "idempotency_key")
    val idempotencyKey: String,
    @ColumnInfo(name = "org_id")
    val orgId: String,
    @ColumnInfo(name = "device_id")
    val deviceId: String,
    val mode: String,
    @ColumnInfo(name = "captured_at_epoch_ms")
    val capturedAtEpochMs: Long,
    @ColumnInfo(name = "created_at_epoch_ms")
    val createdAtEpochMs: Long,
    @ColumnInfo(name = "compression_algorithm")
    val compressionAlgorithm: String,
    @ColumnInfo(name = "payload_compressed")
    val payloadCompressed: ByteArray,
    @ColumnInfo(name = "payload_size_bytes")
    val payloadSizeBytes: Int,
    @ColumnInfo(name = "network_type")
    val networkType: String,
    @ColumnInfo(name = "attempt_count")
    val attemptCount: Int = 0,
    @ColumnInfo(name = "next_retry_at_epoch_ms")
    val nextRetryAtEpochMs: Long,
    @ColumnInfo(name = "last_attempt_at_epoch_ms")
    val lastAttemptAtEpochMs: Long? = null,
    @ColumnInfo(name = "uploaded_at_epoch_ms")
    val uploadedAtEpochMs: Long? = null,
    @ColumnInfo(name = "last_error")
    val lastError: String? = null,
)
