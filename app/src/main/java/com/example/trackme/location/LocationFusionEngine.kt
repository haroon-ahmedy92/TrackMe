package com.example.trackme.location

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import android.os.BatteryManager
import androidx.core.content.ContextCompat
import androidx.core.location.LocationCompat
import com.example.trackme.core.TimeProvider
import com.example.trackme.domain.model.LocationSnapshot
import com.example.trackme.domain.model.MotionState
import com.example.trackme.domain.model.NetworkType
import com.google.android.gms.location.FusedLocationProviderClient
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.tasks.await
import javax.inject.Inject

class LocationFusionEngine @Inject constructor(
    @ApplicationContext private val context: Context,
    private val fusedLocationClient: FusedLocationProviderClient,
    private val timeProvider: TimeProvider,
    private val locationManager: LocationManager,
    private val ipApproximateLocationProvider: IpApproximateLocationProvider,
    private val locationConfidenceScorer: LocationConfidenceScorer,
    private val networkContextCollector: NetworkContextCollector,
    private val motionContextProvider: MotionContextProvider,
    private val geofenceEventContextProvider: GeofenceEventContextProvider,
    private val wifiRttCapabilityChecker: WifiRttCapabilityChecker,
    private val batteryManager: BatteryManager,
    private val spoofingDetector: LocationSpoofingDetector
) {
    suspend fun capture(source: String): LocationSnapshot? {
        if (!hasLocationPermission()) return null

        val now = timeProvider.nowEpochMillis()
        val candidates = mutableListOf<LocationCandidate>()
        val sourceSignals = linkedSetOf<String>()

        runCatching { fusedLocationClient.lastLocation.await() }
            .getOrNull()
            ?.let { location ->
                candidates += location.toCandidate(
                    signalId = "fused_last_known",
                    methodLabel = "Fused location",
                    isApproximate = location.accuracy > 300f
                )
            }

        readLastKnown(LocationManager.GPS_PROVIDER)?.let { location ->
            candidates += location.toCandidate(
                signalId = "gps_last_known",
                methodLabel = "GPS provider",
                isApproximate = false
            )
        }

        readLastKnown(LocationManager.NETWORK_PROVIDER)?.let { location ->
            candidates += location.toCandidate(
                signalId = "network_last_known",
                methodLabel = "Network provider",
                isApproximate = true
            )
        }

        ipApproximateLocationProvider.estimateApproximateLocation()?.let { approximate ->
            candidates += LocationCandidate(
                signalId = "ip_approximate",
                latitude = approximate.latitude,
                longitude = approximate.longitude,
                accuracyMeters = approximate.accuracyMeters,
                capturedAtEpochMs = now,
                methodLabel = "IP-derived approximate location",
                isApproximate = true,
                speedMetersPerSecond = null,
                isMockProvider = false
            )
        }

        if (candidates.isEmpty()) return null

        val geofenceEvent = geofenceEventContextProvider.latestEvent(maxAgeMs = GEOFENCE_CONTEXT_MAX_AGE_MS)

        val evaluations = candidates.map { candidate ->
            val motionState = motionContextProvider.resolveMotionState(candidate.speedMetersPerSecond)
            val spoofing = spoofingDetector.assess(
                signal = SpoofingSignal(
                    isMockProvider = candidate.isMockProvider,
                    capturedAtEpochMs = candidate.capturedAtEpochMs,
                    accuracyMeters = candidate.accuracyMeters,
                    speedMetersPerSecond = candidate.speedMetersPerSecond
                ),
                nowEpochMs = now
            )
            val score = locationConfidenceScorer.score(
                accuracyMeters = candidate.accuracyMeters,
                capturedAtEpochMs = candidate.capturedAtEpochMs,
                nowEpochMs = now,
                isApproximate = candidate.isApproximate,
                sourceCount = candidates.size,
                hasRecentGeofenceEvent = geofenceEvent != null,
                motionState = motionState,
                suspiciousMock = spoofing.suspicious
            )
            CandidateEvaluation(
                candidate = candidate,
                confidenceScore = score,
                motionState = motionState,
                spoofingAssessment = spoofing
            )
        }

        val best = evaluations.maxBy { it.confidenceScore }
        sourceSignals.addAll(candidates.map { it.signalId })

        val networkContext = networkContextCollector.collect()
        if (networkContext.networkType != NetworkType.NONE) sourceSignals += "network_context"
        if (best.motionState != MotionState.UNKNOWN) sourceSignals += "motion_context"
        if (geofenceEvent != null) sourceSignals += "geofence_event"

        val precision = locationConfidenceScorer.classifyPrecision(
            accuracyMeters = best.candidate.accuracyMeters,
            isApproximate = best.candidate.isApproximate
        )
        val batteryLevelPercent = batteryManager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
            .takeIf { it in 0..100 }

        return LocationSnapshot(
            latitude = best.candidate.latitude,
            longitude = best.candidate.longitude,
            accuracyMeters = best.candidate.accuracyMeters,
            capturedAtEpochMs = best.candidate.capturedAtEpochMs,
            source = source,
            methodLabel = best.candidate.methodLabel,
            isApproximate = best.candidate.isApproximate,
            confidenceScore = best.confidenceScore,
            precision = precision,
            sourceSignals = sourceSignals.toList().sorted(),
            batteryLevelPercent = batteryLevelPercent,
            networkType = networkContext.networkType,
            motionState = best.motionState,
            hashedWifiSsid = networkContext.hashedWifiSsid,
            hashedWifiBssid = networkContext.hashedWifiBssid,
            geofenceTransition = geofenceEvent?.transition,
            wifiRttCapable = wifiRttCapabilityChecker.isSupported(),
            suspiciousMockLocation = best.spoofingAssessment.suspicious,
            spoofingReasons = best.spoofingAssessment.reasonCodes
        )
    }

    private fun hasLocationPermission(): Boolean {
        val fine = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)
        val coarse = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION)
        return fine == PackageManager.PERMISSION_GRANTED || coarse == PackageManager.PERMISSION_GRANTED
    }

    private fun readLastKnown(provider: String): Location? {
        return runCatching { locationManager.getLastKnownLocation(provider) }.getOrNull()
    }

    private fun Location.toCandidate(
        signalId: String,
        methodLabel: String,
        isApproximate: Boolean
    ): LocationCandidate {
        val capturedAt = if (time > 0) time else timeProvider.nowEpochMillis()
        val speedMetersPerSecond = if (hasSpeed()) speed else null
        return LocationCandidate(
            signalId = signalId,
            latitude = latitude,
            longitude = longitude,
            accuracyMeters = accuracy,
            capturedAtEpochMs = capturedAt,
            methodLabel = methodLabel,
            isApproximate = isApproximate,
            speedMetersPerSecond = speedMetersPerSecond,
            isMockProvider = LocationCompat.isMock(this)
        )
    }

    private data class LocationCandidate(
        val signalId: String,
        val latitude: Double,
        val longitude: Double,
        val accuracyMeters: Float,
        val capturedAtEpochMs: Long,
        val methodLabel: String,
        val isApproximate: Boolean,
        val speedMetersPerSecond: Float?,
        val isMockProvider: Boolean
    )

    private data class CandidateEvaluation(
        val candidate: LocationCandidate,
        val confidenceScore: Int,
        val motionState: MotionState,
        val spoofingAssessment: SpoofingAssessment
    )

    companion object {
        private const val GEOFENCE_CONTEXT_MAX_AGE_MS = 30 * 60_000L
    }
}
