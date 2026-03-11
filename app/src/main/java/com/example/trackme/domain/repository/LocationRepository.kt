package com.example.trackme.domain.repository

import com.example.trackme.domain.model.LocationSnapshot
import kotlinx.coroutines.flow.Flow

interface LocationRepository {
    fun observeLastKnownLocation(): Flow<LocationSnapshot?>
    suspend fun captureCurrentLocation(source: String): LocationSnapshot?
}
