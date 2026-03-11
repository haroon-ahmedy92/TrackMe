package com.example.trackme.domain.repository

interface IncidentActionScheduler {
    suspend fun scheduleDelayedWipe(executeAtEpochMs: Long)
    suspend fun cancelDelayedWipe()
}
