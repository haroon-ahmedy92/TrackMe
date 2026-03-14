package com.example.trackme.worker

import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.example.trackme.data.preferences.TrackingPreferencesDataSource
import kotlinx.coroutines.flow.first
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class CheckInSchedulerImpl @Inject constructor(
    private val workManager: WorkManager,
    private val preferences: TrackingPreferencesDataSource
) : CheckInScheduler {

    override suspend fun scheduleNormalCheckIn() {
        val consentGranted = preferences.explicitTrackingConsentGranted.first()
        if (!consentGranted) {
            workManager.cancelUniqueWork(NORMAL_WORK_NAME)
            return
        }
        val intervalMinutes = preferences.normalIntervalMinutes.first().coerceAtLeast(MIN_WORK_INTERVAL_MINUTES)
        val request = PeriodicWorkRequestBuilder<NormalCheckInWorker>(intervalMinutes, TimeUnit.MINUTES)
            .setConstraints(defaultConstraints())
            .build()

        workManager.enqueueUniquePeriodicWork(
            NORMAL_WORK_NAME,
            ExistingPeriodicWorkPolicy.UPDATE,
            request
        )
    }

    override suspend fun scheduleMisplacedCheckIn() {
        val consentGranted = preferences.explicitTrackingConsentGranted.first()
        if (!consentGranted) {
            workManager.cancelUniqueWork(MISPLACED_WORK_NAME)
            return
        }
        val intervalMinutes = preferences.misplacedIntervalMinutes.first().coerceAtLeast(MIN_WORK_INTERVAL_MINUTES)
        val request = PeriodicWorkRequestBuilder<MisplacedCheckInWorker>(intervalMinutes, TimeUnit.MINUTES)
            .setConstraints(defaultConstraints())
            .build()

        workManager.enqueueUniquePeriodicWork(
            MISPLACED_WORK_NAME,
            ExistingPeriodicWorkPolicy.UPDATE,
            request
        )
    }

    override suspend fun scheduleLostModeCheckIn(untilEpochMs: Long) {
        val consentGranted = preferences.explicitTrackingConsentGranted.first()
        if (!consentGranted) {
            workManager.cancelUniqueWork(LOST_WORK_NAME)
            return
        }
        val intervalMinutes = preferences.lostModeIntervalMinutes.first().coerceAtLeast(MIN_WORK_INTERVAL_MINUTES)
        val request = PeriodicWorkRequestBuilder<LostModeCheckInWorker>(intervalMinutes, TimeUnit.MINUTES)
            .setInputData(LostModeCheckInWorker.inputData(untilEpochMs))
            .setConstraints(defaultConstraints())
            .build()

        workManager.enqueueUniquePeriodicWork(
            LOST_WORK_NAME,
            ExistingPeriodicWorkPolicy.UPDATE,
            request
        )
    }

    override suspend fun cancelLostModeCheckIn() {
        workManager.cancelUniqueWork(LOST_WORK_NAME)
    }

    override suspend fun cancelMisplacedCheckIn() {
        workManager.cancelUniqueWork(MISPLACED_WORK_NAME)
    }

    private fun defaultConstraints(): Constraints {
        return Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .setRequiresBatteryNotLow(true)
            .build()
    }

    companion object {
        private const val MIN_WORK_INTERVAL_MINUTES = 15L
        const val NORMAL_WORK_NAME = "normal_check_in"
        const val MISPLACED_WORK_NAME = "misplaced_check_in"
        const val LOST_WORK_NAME = "lost_mode_check_in"
    }
}
