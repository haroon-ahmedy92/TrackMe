package com.example.trackme.domain.repository

interface IntegrityRepository {
    suspend fun getIntegrityTokenOrNull(): String?
}
