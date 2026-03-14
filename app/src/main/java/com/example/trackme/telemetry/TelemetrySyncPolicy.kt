package com.example.trackme.telemetry

import com.example.trackme.domain.model.CheckInMode
import com.example.trackme.domain.model.NetworkType
import javax.inject.Inject
import javax.inject.Singleton

data class TelemetryBatchPolicy(
    val shouldSync: Boolean,
    val maxBatchSize: Int,
    val transportLabel: String,
)

@Singleton
class TelemetrySyncPolicy @Inject constructor() {
    fun resolve(networkType: NetworkType, modes: List<CheckInMode>): TelemetryBatchPolicy {
        val highPriority = modes.any { it == CheckInMode.LOST_MODE }
        return when (networkType) {
            NetworkType.WIFI, NetworkType.ETHERNET -> TelemetryBatchPolicy(true, 25, "unmetered")
            NetworkType.CELLULAR -> TelemetryBatchPolicy(true, if (highPriority) 10 else 5, "metered")
            NetworkType.UNKNOWN -> TelemetryBatchPolicy(true, if (highPriority) 8 else 4, "unknown")
            NetworkType.NONE -> TelemetryBatchPolicy(false, 0, "offline")
        }
    }
}
