package com.example.trackme.commands

import com.example.trackme.domain.usecase.SetLostModeUseCase
import javax.inject.Inject
import javax.inject.Singleton

interface LostModeCommandExecutor {
    suspend fun enable(untilEpochMs: Long)
}

@Singleton
class UseCaseLostModeCommandExecutor @Inject constructor(
    private val setLostModeUseCase: SetLostModeUseCase,
) : LostModeCommandExecutor {
    override suspend fun enable(untilEpochMs: Long) {
        setLostModeUseCase.enable(untilEpochMs)
    }
}
