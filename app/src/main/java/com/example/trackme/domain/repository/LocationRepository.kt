package com.example.trackme.domain.repository

import com.example.trackme.domain.model.LocationSnapshot
import kotlinx.coroutines.flow.Flow

interface LocationRepository {
    fun observeLastKnownLocation(): Flow<LocationSnapshot?>
    fun observeRecentHistory(limit: Int = 24): Flow<List<LocationSnapshot>>
    suspend fun captureCurrentLocation(source: String): LocationSnapshot?
}
