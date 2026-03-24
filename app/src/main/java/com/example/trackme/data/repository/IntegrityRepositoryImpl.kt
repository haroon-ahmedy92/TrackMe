package com.example.trackme.data.repository

import com.example.trackme.domain.repository.IntegrityRepository
import com.example.trackme.trust.IntegritySignal
import com.example.trackme.trust.IntegritySignalProvider
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow

@Singleton
class IntegrityRepositoryImpl @Inject constructor(
    private val integritySignalProvider: IntegritySignalProvider,
) : IntegrityRepository {
    override suspend fun getIntegritySignal(): IntegritySignal = integritySignalProvider.currentSignal()

    override fun observeIntegritySignal(): Flow<IntegritySignal> = integritySignalProvider.observeSignal()
}
