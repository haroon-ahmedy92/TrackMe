package com.example.trackme.ui.map

import com.example.trackme.BuildConfig
import com.example.trackme.domain.model.LocationPrecision
import com.example.trackme.domain.model.LocationSnapshot
import com.example.trackme.feature.common.LocationFreshness
import com.example.trackme.feature.common.freshness
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import javax.inject.Inject

data class MapPoint(
    val latitude: Double,
    val longitude: Double,
    val precision: LocationPrecision,
    val isApproximate: Boolean,
    val freshness: LocationFreshness,
)

data class MapRenderSpec(
    val providerName: String,
    val staticMapUrl: String?,
    val interactiveUrl: String?,
    val configured: Boolean,
)

interface MapProvider {
    val providerName: String
    fun formatMarkerTitle(location: LocationSnapshot): String
    fun render(history: List<LocationSnapshot>): MapRenderSpec
}

class GoogleMapProvider @Inject constructor() : MapProvider {
    override val providerName: String = BuildConfig.TRACKME_MAP_PROVIDER.lowercase()

    override fun formatMarkerTitle(location: LocationSnapshot): String {
        return "${location.methodLabel} (${location.confidenceScore}/100)"
    }

    override fun render(history: List<LocationSnapshot>): MapRenderSpec {
        val points = history.map {
            MapPoint(
                latitude = it.latitude,
                longitude = it.longitude,
                precision = it.precision,
                isApproximate = it.isApproximate,
                freshness = it.freshness(),
            )
        }
        return when (providerName) {
            "mapbox" -> buildMapbox(points)
            else -> buildGoogle(points)
        }
    }

    private fun buildGoogle(points: List<MapPoint>): MapRenderSpec {
        if (BuildConfig.TRACKME_GOOGLE_STATIC_MAPS_API_KEY.isBlank() || points.isEmpty()) {
            return MapRenderSpec(
                providerName = "Google Maps",
                staticMapUrl = null,
                interactiveUrl = null,
                configured = BuildConfig.TRACKME_GOOGLE_STATIC_MAPS_API_KEY.isNotBlank(),
            )
        }
        val params = mutableListOf(
            "size=640x360",
            "scale=2",
            "key=${encode(BuildConfig.TRACKME_GOOGLE_STATIC_MAPS_API_KEY)}",
        )
        points.forEach { point ->
            params += "visible=${encode("${point.latitude},${point.longitude}")}"
        }
        if (points.size > 1) {
            params += "path=${encode("color:0x006f8bAA|weight:4|" + points.joinToString("|") { "${it.latitude},${it.longitude}" })}"
        }
        points.forEach { point ->
            params += "markers=${encode("size:mid|color:${googleColor(colorForPoint(point))}|label:${labelForPoint(point)}|${point.latitude},${point.longitude}")}"
        }
        val primary = points.last()
        return MapRenderSpec(
            providerName = "Google Maps",
            staticMapUrl = "https://maps.googleapis.com/maps/api/staticmap?${params.joinToString("&")}",
            interactiveUrl = "https://www.google.com/maps/search/?api=1&query=${primary.latitude},${primary.longitude}",
            configured = true,
        )
    }

    private fun buildMapbox(points: List<MapPoint>): MapRenderSpec {
        if (BuildConfig.TRACKME_MAPBOX_ACCESS_TOKEN.isBlank() || points.isEmpty()) {
            return MapRenderSpec(
                providerName = "Mapbox",
                staticMapUrl = null,
                interactiveUrl = null,
                configured = BuildConfig.TRACKME_MAPBOX_ACCESS_TOKEN.isNotBlank(),
            )
        }
        val features = mutableListOf<String>()
        if (points.size > 1) {
            features += """
                {"type":"Feature","properties":{"stroke":"#006f8b","stroke-width":4,"stroke-opacity":0.85},"geometry":{"type":"LineString","coordinates":[${points.joinToString(",") { "[${it.longitude},${it.latitude}]" }}]}}
            """.trimIndent()
        }
        points.forEach { point ->
            features += """
                {"type":"Feature","properties":{"marker-color":"${colorForPoint(point)}","marker-size":"${if (point.isApproximate) "small" else "medium"}","title":"${labelForPoint(point)}"},"geometry":{"type":"Point","coordinates":[${point.longitude},${point.latitude}]}}
            """.trimIndent()
        }
        val featureCollection = """{"type":"FeatureCollection","features":[${features.joinToString(",")}]}"""
        val staticUrl =
            "https://api.mapbox.com/styles/v1/${BuildConfig.TRACKME_MAPBOX_USERNAME}/${BuildConfig.TRACKME_MAPBOX_STYLE_ID}/static/geojson(${encode(featureCollection)})/auto/640x360?padding=48&access_token=${encode(BuildConfig.TRACKME_MAPBOX_ACCESS_TOKEN)}"
        return MapRenderSpec(
            providerName = "Mapbox",
            staticMapUrl = staticUrl,
            interactiveUrl = null,
            configured = true,
        )
    }

    private fun colorForPoint(point: MapPoint): String = when {
        point.freshness == LocationFreshness.OFFLINE -> "#64748b"
        point.freshness == LocationFreshness.STALE -> "#c2410c"
        point.isApproximate || point.precision == LocationPrecision.APPROXIMATE -> "#6b7280"
        point.precision == LocationPrecision.MODERATE -> "#a16207"
        else -> "#0f766e"
    }

    private fun labelForPoint(point: MapPoint): String = when {
        point.freshness == LocationFreshness.OFFLINE -> "O"
        point.freshness == LocationFreshness.STALE -> "S"
        point.isApproximate || point.precision == LocationPrecision.APPROXIMATE -> "A"
        point.precision == LocationPrecision.MODERATE -> "M"
        else -> "P"
    }

    private fun googleColor(value: String): String = "0x${value.removePrefix("#")}"

    private fun encode(value: String): String = URLEncoder.encode(value, StandardCharsets.UTF_8.toString())
}
