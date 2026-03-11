package com.example.trackme.data.network

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
