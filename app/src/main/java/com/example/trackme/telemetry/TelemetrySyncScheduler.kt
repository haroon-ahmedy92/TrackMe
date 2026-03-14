package com.example.trackme.telemetry

import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.example.trackme.worker.TelemetrySyncWorker
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class TelemetrySyncScheduler @Inject constructor(
    private val workManager: WorkManager,
) {
    suspend fun scheduleImmediateSync() {
        val request = OneTimeWorkRequestBuilder<TelemetrySyncWorker>()
            .setConstraints(immediateConstraints())
            .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 1, TimeUnit.MINUTES)
            .build()
        workManager.enqueueUniqueWork(IMMEDIATE_WORK_NAME, ExistingWorkPolicy.REPLACE, request)
    }

    suspend fun schedulePeriodicSync() {
        val request = PeriodicWorkRequestBuilder<TelemetrySyncWorker>(SYNC_INTERVAL_MINUTES, TimeUnit.MINUTES)
            .setConstraints(periodicConstraints())
            .build()
        workManager.enqueueUniquePeriodicWork(PERIODIC_WORK_NAME, ExistingPeriodicWorkPolicy.UPDATE, request)
    }

    private fun immediateConstraints(): Constraints {
        return Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
    }

    private fun periodicConstraints(): Constraints {
        return Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(true)
            .build()
    }

    companion object {
        const val IMMEDIATE_WORK_NAME = "telemetry_sync_now"
        const val PERIODIC_WORK_NAME = "telemetry_sync_periodic"
        private const val SYNC_INTERVAL_MINUTES = 15L
    }
}
