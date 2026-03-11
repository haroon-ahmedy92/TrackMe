package com.example.trackme.worker

interface CheckInScheduler {
    suspend fun scheduleNormalCheckIn()
    suspend fun scheduleLostModeCheckIn(untilEpochMs: Long)
    suspend fun cancelLostModeCheckIn()
}
