package com.example.trackme.domain.repository

import com.example.trackme.data.network.PlatformLocationIngestRequestDto

interface TelemetrySyncRepository {
    suspend fun enqueue(request: PlatformLocationIngestRequestDto)
    suspend fun syncPending()
    suspend fun pendingCount(): Int
}
