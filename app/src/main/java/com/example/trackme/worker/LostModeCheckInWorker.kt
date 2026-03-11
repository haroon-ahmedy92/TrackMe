package com.example.trackme.worker

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.Data
import androidx.work.WorkerParameters
import com.example.trackme.core.TimeProvider
import com.example.trackme.domain.model.CheckInMode
import com.example.trackme.domain.usecase.PerformCheckInUseCase
import com.example.trackme.domain.usecase.SetLostModeUseCase
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

@HiltWorker
class LostModeCheckInWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted workerParams: WorkerParameters,
    private val timeProvider: TimeProvider,
    private val performCheckInUseCase: PerformCheckInUseCase,
    private val setLostModeUseCase: SetLostModeUseCase
) : CoroutineWorker(context, workerParams) {

    override suspend fun doWork(): Result {
        val untilEpochMs = inputData.getLong(KEY_UNTIL_EPOCH_MS, 0L)
        if (untilEpochMs > 0 && timeProvider.nowEpochMillis() > untilEpochMs) {
            setLostModeUseCase.disable()
            return Result.success()
        }

        return runCatching {
            performCheckInUseCase(mode = CheckInMode.LOST_MODE, source = "lost_mode_worker")
        }.fold(
            onSuccess = { Result.success() },
            onFailure = { Result.retry() }
        )
    }

    companion object {
        private const val KEY_UNTIL_EPOCH_MS = "key_until_epoch_ms"

        fun inputData(untilEpochMs: Long): Data {
            return Data.Builder()
                .putLong(KEY_UNTIL_EPOCH_MS, untilEpochMs)
                .build()
        }
    }
}
