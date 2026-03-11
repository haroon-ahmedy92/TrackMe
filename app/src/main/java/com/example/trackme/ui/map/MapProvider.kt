package com.example.trackme.ui.map

import com.example.trackme.domain.model.LocationSnapshot
import javax.inject.Inject

/**
 * Map SDK abstraction layer so app logic does not depend directly on Google/Mapbox APIs.
 */
interface MapProvider {
    val providerName: String
    fun formatMarkerTitle(location: LocationSnapshot): String
}

class GoogleMapProvider @Inject constructor() : MapProvider {
    override val providerName: String = "google_maps"

    override fun formatMarkerTitle(location: LocationSnapshot): String {
        return "${location.methodLabel} (${location.confidenceScore}/100)"
    }
}
