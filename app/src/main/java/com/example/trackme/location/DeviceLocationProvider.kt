package com.example.trackme.location

import com.example.trackme.domain.model.LocationSnapshot

interface DeviceLocationProvider {
    suspend fun getCurrentLocation(source: String): LocationSnapshot?
}
