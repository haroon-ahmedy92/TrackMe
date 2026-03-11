package com.example.trackme.data.network

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
