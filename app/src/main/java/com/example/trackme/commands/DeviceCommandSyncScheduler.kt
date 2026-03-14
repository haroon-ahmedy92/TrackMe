package com.example.trackme.commands

import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.example.trackme.worker.DeviceCommandSyncWorker
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class DeviceCommandSyncScheduler @Inject constructor(
    private val workManager: WorkManager,
) {
    suspend fun scheduleImmediateSync() {
        val request = OneTimeWorkRequestBuilder<DeviceCommandSyncWorker>()
            .setConstraints(defaultConstraints())
            .build()
        workManager.enqueueUniqueWork(IMMEDIATE_WORK_NAME, ExistingWorkPolicy.REPLACE, request)
    }

    suspend fun schedulePeriodicSync() {
        val request = PeriodicWorkRequestBuilder<DeviceCommandSyncWorker>(SYNC_INTERVAL_MINUTES, TimeUnit.MINUTES)
            .setConstraints(defaultConstraints())
            .build()
        workManager.enqueueUniquePeriodicWork(PERIODIC_WORK_NAME, ExistingPeriodicWorkPolicy.UPDATE, request)
    }

    private fun defaultConstraints(): Constraints {
        return Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(true)
            .build()
    }

    companion object {
        const val IMMEDIATE_WORK_NAME = "device_command_sync_now"
        const val PERIODIC_WORK_NAME = "device_command_sync_periodic"
        private const val SYNC_INTERVAL_MINUTES = 15L
    }
}
