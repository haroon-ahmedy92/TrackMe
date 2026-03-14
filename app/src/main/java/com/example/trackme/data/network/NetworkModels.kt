package com.example.trackme.data.network

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class CheckInRequest(
    val deviceAlias: String,
    val mode: String,
    val checkInAtEpochMs: Long,
    val batteryPercent: Int?,
    val location: LocationTelemetryDto?,
    val integrityVerdict: String,
    val telemetrySignature: String,
    val telemetryKeyId: String,
    val telemetryPayloadHash: String
)

@Serializable
data class LocationTelemetryDto(
    val latitude: Double?,
    val longitude: Double?,
    val accuracyMeters: Float?,
    val capturedAtEpochMs: Long?,
    val source: String?,
    val sourceSignals: List<String> = emptyList(),
    val confidenceScore: Int?,
    val precision: String?,
    val isApproximate: Boolean?,
    val methodLabel: String?,
    val networkType: String?,
    val motionState: String?,
    val hashedWifiSsid: String?,
    val hashedWifiBssid: String?,
    val geofenceTransition: String?,
    val wifiRttCapable: Boolean?,
    val suspiciousMockLocation: Boolean?,
    val spoofingReasons: List<String> = emptyList()
)

@Serializable
data class AuditEventRequest(
    val type: String,
    val summary: String,
    val metadataJson: String,
    val createdAtEpochMs: Long,
    val hash: String
)

@Serializable
data class PairingCompleteRequestDto(
    val token: String? = null,
    val qrPayload: String? = null,
    val alias: String,
    val ownerSubject: String? = null,
    val keyId: String,
    val publicKeyPem: String,
    val algorithm: String,
)

@Serializable
data class OwnershipBindingResponseDto(
    @SerialName("ownership_binding_id") val ownershipBindingId: String,
    @SerialName("org_id") val orgId: String,
    @SerialName("device_id") val deviceId: String,
    @SerialName("owner_subject") val ownerSubject: String? = null,
    @SerialName("ownership_type") val ownershipType: String,
    @SerialName("proof_kind") val proofKind: String,
    @SerialName("consent_version") val consentVersion: String,
    @SerialName("consent_captured_at") val consentCapturedAt: String,
    @SerialName("is_active") val isActive: Boolean,
    @SerialName("created_at") val createdAt: String,
    @SerialName("ended_at") val endedAt: String? = null,
)

@Serializable
data class DevicePushTokenRegistrationRequestDto(
    val orgId: String,
    val deviceId: String,
    val keyId: String,
    val pushToken: String,
    val appVersion: String? = null,
)

@Serializable
data class DeviceCommandSyncRequestDto(
    val orgId: String,
    val deviceId: String,
    val keyId: String,
)

@Serializable
data class CommandEnvelopeDto(
    val remoteActionId: String,
    val orgId: String,
    val deviceId: String,
    val incidentId: String? = null,
    val actionKind: String,
    val state: String,
    val reason: String,
    val payload: Map<String, kotlinx.serialization.json.JsonElement>,
    val signature: String,
    val signatureAlgorithm: String,
    val requestedBySub: String,
    val requestedAt: String,
    val expiresAt: String? = null,
)

@Serializable
data class CommandAckRequestDto(
    val orgId: String,
    val deviceId: String,
    val keyId: String,
    val status: String,
    val errorMessage: String? = null,
    val metadata: Map<String, String> = emptyMap(),
)
