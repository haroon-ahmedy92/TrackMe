package com.example.trackme.worker

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.example.trackme.domain.model.CheckInMode
import com.example.trackme.domain.usecase.PerformCheckInUseCase
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

@HiltWorker
class NormalCheckInWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted workerParams: WorkerParameters,
    private val performCheckInUseCase: PerformCheckInUseCase
) : CoroutineWorker(context, workerParams) {

    override suspend fun doWork(): Result {
        return runCatching {
            performCheckInUseCase(mode = CheckInMode.NORMAL, source = "normal_worker")
        }.fold(
            onSuccess = { Result.success() },
            onFailure = { Result.retry() }
        )
    }
}
