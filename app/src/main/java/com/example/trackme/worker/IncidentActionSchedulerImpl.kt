package com.example.trackme.worker

import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import com.example.trackme.core.TimeProvider
import com.example.trackme.domain.repository.IncidentActionScheduler
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class IncidentActionSchedulerImpl @Inject constructor(
    private val workManager: WorkManager,
    private val timeProvider: TimeProvider
) : IncidentActionScheduler {

    override suspend fun scheduleDelayedWipe(executeAtEpochMs: Long) {
        val initialDelayMs = (executeAtEpochMs - timeProvider.nowEpochMillis()).coerceAtLeast(0L)
        val request = OneTimeWorkRequestBuilder<DelayedWipeWorker>()
            .setInitialDelay(initialDelayMs, TimeUnit.MILLISECONDS)
            .setConstraints(defaultConstraints())
            .build()

        workManager.enqueueUniqueWork(
            DELAYED_WIPE_WORK_NAME,
            ExistingWorkPolicy.REPLACE,
            request
        )
    }

    override suspend fun cancelDelayedWipe() {
        workManager.cancelUniqueWork(DELAYED_WIPE_WORK_NAME)
    }

    private fun defaultConstraints(): Constraints {
        return Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(true)
            .build()
    }

    companion object {
        const val DELAYED_WIPE_WORK_NAME = "incident_delayed_remote_wipe"
    }
}
