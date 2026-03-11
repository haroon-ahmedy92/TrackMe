package com.example.trackme.domain.model

data class LocationSnapshot(
    val latitude: Double,
    val longitude: Double,
    val accuracyMeters: Float,
    val capturedAtEpochMs: Long,
    val source: String,
    val methodLabel: String,
    val isApproximate: Boolean,
    val confidenceScore: Int,
    val precision: LocationPrecision = if (isApproximate) {
        LocationPrecision.APPROXIMATE
    } else {
        LocationPrecision.MODERATE
    },
    val sourceSignals: List<String> = listOf(methodLabel),
    val batteryLevelPercent: Int? = null,
    val networkType: NetworkType = NetworkType.UNKNOWN,
    val motionState: MotionState = MotionState.UNKNOWN,
    val hashedWifiSsid: String? = null,
    val hashedWifiBssid: String? = null,
    val geofenceTransition: String? = null,
    val wifiRttCapable: Boolean = false,
    val suspiciousMockLocation: Boolean = false,
    val spoofingReasons: List<String> = emptyList()
)
