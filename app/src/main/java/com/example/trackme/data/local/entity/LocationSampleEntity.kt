package com.example.trackme.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "location_samples")
data class LocationSampleEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val latitude: Double,
    val longitude: Double,
    val accuracyMeters: Float,
    val capturedAtEpochMs: Long,
    val source: String,
    val methodLabel: String,
    val isApproximate: Boolean,
    val confidenceScore: Int,
    val precision: String,
    val sourceSignalsCsv: String,
    val batteryLevelPercent: Int?,
    val networkType: String,
    val motionState: String,
    val hashedWifiSsid: String?,
    val hashedWifiBssid: String?,
    val geofenceTransition: String?,
    val wifiRttCapable: Boolean,
    val suspiciousMockLocation: Boolean,
    val spoofingReasonsCsv: String
)
