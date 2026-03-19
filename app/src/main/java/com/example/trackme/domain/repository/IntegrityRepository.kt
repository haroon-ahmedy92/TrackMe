package com.example.trackme.domain.repository

import com.example.trackme.trust.IntegritySignal
import kotlinx.coroutines.flow.Flow

interface IntegrityRepository {
    suspend fun getIntegritySignal(): IntegritySignal
    fun observeIntegritySignal(): Flow<IntegritySignal>
}
