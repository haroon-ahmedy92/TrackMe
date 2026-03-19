package com.example.trackme.data.repository

import com.example.trackme.domain.repository.IntegrityRepository
import com.example.trackme.trust.IntegritySignal
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf

@Singleton
class IntegrityRepositoryImpl @Inject constructor() : IntegrityRepository {
    override suspend fun getIntegritySignal(): IntegritySignal = currentSignal()

    override fun observeIntegritySignal(): Flow<IntegritySignal> = flowOf(currentSignal())

    private fun currentSignal(): IntegritySignal {
        // Placeholder for Play Integrity API integration.
        return IntegritySignal(
            token = null,
            status = "unavailable",
            trusted = false,
            provider = "play_integrity_placeholder",
        )
    }
}
