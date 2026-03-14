package com.example.trackme.worker

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.example.trackme.commands.DeviceCommandSyncOrchestrator
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

@HiltWorker
class DeviceCommandSyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted workerParams: WorkerParameters,
    private val orchestrator: DeviceCommandSyncOrchestrator,
) : CoroutineWorker(context, workerParams) {

    override suspend fun doWork(): Result {
        return runCatching {
            orchestrator.syncAndProcess()
        }.fold(
            onSuccess = { Result.success() },
            onFailure = { Result.retry() },
        )
    }
}
