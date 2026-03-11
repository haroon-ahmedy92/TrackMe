package com.example.trackme.data.repository

import com.example.trackme.data.local.dao.DeviceStateDao
import com.example.trackme.data.local.entity.DeviceStateEntity
import com.example.trackme.domain.model.CheckInMode
import com.example.trackme.domain.model.DeviceState
import com.example.trackme.domain.repository.DeviceStateRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class DeviceStateRepositoryImpl @Inject constructor(
    private val deviceStateDao: DeviceStateDao
) : DeviceStateRepository {

    override fun observeDeviceState(): Flow<DeviceState> {
        return deviceStateDao.observeById().map { entity ->
            entity?.toDomain() ?: DeviceState(
                mode = CheckInMode.NORMAL,
                lastCheckInEpochMs = null,
                batteryPercent = null,
                lostModeUntilEpochMs = null
            )
        }
    }

    override suspend fun updateCheckIn(mode: CheckInMode, batteryPercent: Int?, checkInAtEpochMs: Long) {
        val current = deviceStateDao.observeById().first()
        deviceStateDao.upsert(
            DeviceStateEntity(
                id = DeviceStateEntity.SINGLETON_ID,
                mode = mode.name,
                lastCheckInEpochMs = checkInAtEpochMs,
                batteryPercent = batteryPercent,
                lostModeUntilEpochMs = current?.lostModeUntilEpochMs
            )
        )
    }

    override suspend fun setLostMode(untilEpochMs: Long?) {
        val current = deviceStateDao.observeById().first()
        val mode = if (untilEpochMs == null) CheckInMode.NORMAL else CheckInMode.LOST_MODE
        deviceStateDao.upsert(
            DeviceStateEntity(
                id = DeviceStateEntity.SINGLETON_ID,
                mode = mode.name,
                lastCheckInEpochMs = current?.lastCheckInEpochMs,
                batteryPercent = current?.batteryPercent,
                lostModeUntilEpochMs = untilEpochMs
            )
        )
    }

    private fun DeviceStateEntity.toDomain(): DeviceState {
        return DeviceState(
            mode = runCatching { CheckInMode.valueOf(mode) }.getOrDefault(CheckInMode.NORMAL),
            lastCheckInEpochMs = lastCheckInEpochMs,
            batteryPercent = batteryPercent,
            lostModeUntilEpochMs = lostModeUntilEpochMs
        )
    }
}
