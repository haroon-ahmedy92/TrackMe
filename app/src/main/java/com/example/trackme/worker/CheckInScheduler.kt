package com.example.trackme.worker

interface CheckInScheduler {
    suspend fun scheduleNormalCheckIn()
    suspend fun scheduleMisplacedCheckIn()
    suspend fun scheduleLostModeCheckIn(untilEpochMs: Long)
    suspend fun cancelMisplacedCheckIn()
    suspend fun cancelLostModeCheckIn()
}
