package com.example.trackme.location

import com.example.trackme.domain.model.LocationSnapshot
import javax.inject.Inject

class FusedDeviceLocationProvider @Inject constructor(
    private val fusionEngine: LocationFusionEngine
) : DeviceLocationProvider {

    override suspend fun getCurrentLocation(source: String): LocationSnapshot? {
        return fusionEngine.capture(source = source)
    }
}
