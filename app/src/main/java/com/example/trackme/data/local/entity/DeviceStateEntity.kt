package com.example.trackme.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "device_state")
data class DeviceStateEntity(
    @PrimaryKey val id: Int = SINGLETON_ID,
    val mode: String,
    val lastCheckInEpochMs: Long?,
    val batteryPercent: Int?,
    val lostModeUntilEpochMs: Long?
) {
    companion object {
        const val SINGLETON_ID = 1
    }
}
