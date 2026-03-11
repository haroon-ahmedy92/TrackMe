package com.example.trackme.data.repository

import com.example.trackme.domain.repository.IntegrityRepository
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class IntegrityRepositoryImpl @Inject constructor() : IntegrityRepository {
    override suspend fun getIntegrityTokenOrNull(): String? {
        // Placeholder for Play Integrity API integration.
        return null
    }
}
