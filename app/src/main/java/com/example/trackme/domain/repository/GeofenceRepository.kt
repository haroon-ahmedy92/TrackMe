package com.example.trackme.domain.repository

import com.example.trackme.domain.model.GeofenceProtectionConfig
import kotlinx.coroutines.flow.Flow

interface GeofenceRepository {
    fun observeConfig(): Flow<GeofenceProtectionConfig>
    suspend fun setConfig(enabled: Boolean, radiusMeters: Int)
}
