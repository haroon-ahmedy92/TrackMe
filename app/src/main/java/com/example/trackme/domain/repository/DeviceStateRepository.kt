package com.example.trackme.domain.repository

import com.example.trackme.domain.model.CheckInMode
import com.example.trackme.domain.model.DeviceState
import kotlinx.coroutines.flow.Flow

interface DeviceStateRepository {
    fun observeDeviceState(): Flow<DeviceState>
    suspend fun updateCheckIn(mode: CheckInMode, batteryPercent: Int?, checkInAtEpochMs: Long)
    suspend fun setLostMode(untilEpochMs: Long?)
}
