package com.example.trackme.worker

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.example.trackme.domain.usecase.ManageIncidentLifecycleUseCase
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

@HiltWorker
class DelayedWipeWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted workerParams: WorkerParameters,
    private val manageIncidentLifecycleUseCase: ManageIncidentLifecycleUseCase
) : CoroutineWorker(context, workerParams) {

    override suspend fun doWork(): Result {
        return runCatching {
            manageIncidentLifecycleUseCase.executeDelayedWipeIfDue(source = "delayed_wipe_worker")
        }.fold(
            onSuccess = { Result.success() },
            onFailure = { Result.retry() }
        )
    }
}
