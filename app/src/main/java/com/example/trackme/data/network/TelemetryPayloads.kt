package com.example.trackme.data.network

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CheckInTelemetryPayload(
    val mode: String,
    val source: String,
    val checkInAtEpochMs: Long,
    val batteryPercent: Int?,
    val lowBatteryOptimizationApplied: Boolean,
    val location: LocationTelemetryDto?,
    val integrityVerdict: String
)

@Serializable
data class PlatformLocationIngestRequestDto(
    @SerialName("org_id") val orgId: String,
    @SerialName("device_id") val deviceId: String,
    val mode: String,
    @SerialName("idempotency_key") val idempotencyKey: String,
    @SerialName("captured_at") val capturedAt: String,
    @SerialName("captured_at_epoch_ms") val capturedAtEpochMs: Long,
    val latitude: Double? = null,
    val longitude: Double? = null,
    @SerialName("accuracy_meters") val accuracyMeters: Float? = null,
    val precision: String,
    @SerialName("confidence_score") val confidenceScore: Int? = null,
    @SerialName("source_methods") val sourceMethods: List<String> = emptyList(),
    @SerialName("network_type") val networkType: String? = null,
    @SerialName("battery_percent") val batteryPercent: Int? = null,
    @SerialName("motion_state") val motionState: String? = null,
    @SerialName("telemetry_signature") val telemetrySignature: String? = null,
    @SerialName("telemetry_algorithm") val telemetryAlgorithm: String? = null,
    @SerialName("telemetry_key_id") val telemetryKeyId: String? = null,
    @SerialName("telemetry_payload_hash") val telemetryPayloadHash: String? = null,
    @SerialName("integrity_verdict") val integrityVerdict: String? = null,
    @SerialName("ip_address") val ipAddress: String? = null,
)

@Serializable
data class LocationIngestBatchRequestDto(
    val items: List<PlatformLocationIngestRequestDto>,
)

@Serializable
data class LocationIngestBatchItemResultDto(
    @SerialName("idempotency_key") val idempotencyKey: String,
    @SerialName("event_id") val eventId: String? = null,
    val accepted: Boolean,
    val duplicate: Boolean,
    val error: String? = null,
)

@Serializable
data class LocationIngestBatchResponseDto(
    @SerialName("accepted_count") val acceptedCount: Int,
    @SerialName("duplicate_count") val duplicateCount: Int,
    @SerialName("failed_count") val failedCount: Int,
    val results: List<LocationIngestBatchItemResultDto>,
)
