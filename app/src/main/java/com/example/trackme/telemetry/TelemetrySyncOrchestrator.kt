package com.example.trackme.telemetry

import com.example.trackme.domain.repository.TelemetrySyncRepository
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class TelemetrySyncOrchestrator @Inject constructor(
    private val telemetrySyncRepository: TelemetrySyncRepository,
) {
    suspend fun syncPending() {
        telemetrySyncRepository.syncPending()
    }
}
