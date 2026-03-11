package com.example.trackme.data.repository

import com.example.trackme.data.preferences.TrackingPreferencesDataSource
import com.example.trackme.domain.model.GeofenceProtectionConfig
import com.example.trackme.domain.repository.GeofenceRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.combine
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class GeofenceRepositoryImpl @Inject constructor(
    private val preferences: TrackingPreferencesDataSource
) : GeofenceRepository {

    override fun observeConfig(): Flow<GeofenceProtectionConfig> {
        return combine(
            preferences.geofenceProtectionEnabled,
            preferences.geofenceRadiusMeters
        ) { enabled, radiusMeters ->
            GeofenceProtectionConfig(enabled = enabled, radiusMeters = radiusMeters)
        }
    }

    override suspend fun setConfig(enabled: Boolean, radiusMeters: Int) {
        preferences.setGeofenceProtection(enabled = enabled, radiusMeters = radiusMeters)
    }
}
