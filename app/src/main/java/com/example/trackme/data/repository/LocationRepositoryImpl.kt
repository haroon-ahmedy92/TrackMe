package com.example.trackme.data.repository

import com.example.trackme.data.local.dao.LocationDao
import com.example.trackme.data.local.entity.LocationSampleEntity
import com.example.trackme.domain.model.LocationPrecision
import com.example.trackme.domain.model.LocationSnapshot
import com.example.trackme.domain.model.MotionState
import com.example.trackme.domain.model.NetworkType
import com.example.trackme.domain.repository.LocationRepository
import com.example.trackme.location.DeviceLocationProvider
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class LocationRepositoryImpl @Inject constructor(
    private val locationDao: LocationDao,
    private val locationProvider: DeviceLocationProvider
) : LocationRepository {

    override fun observeLastKnownLocation(): Flow<LocationSnapshot?> {
        return locationDao.observeLatest().map { it?.toDomain() }
    }

    override fun observeRecentHistory(limit: Int): Flow<List<LocationSnapshot>> {
        return locationDao.observeRecent(limit).map { entities ->
            entities
                .asReversed()
                .map { it.toDomain() }
        }
    }

    override suspend fun captureCurrentLocation(source: String): LocationSnapshot? {
        val snapshot = locationProvider.getCurrentLocation(source) ?: return null
        locationDao.insert(
            LocationSampleEntity(
                latitude = snapshot.latitude,
                longitude = snapshot.longitude,
                accuracyMeters = snapshot.accuracyMeters,
                capturedAtEpochMs = snapshot.capturedAtEpochMs,
                source = snapshot.source,
                methodLabel = snapshot.methodLabel,
                isApproximate = snapshot.isApproximate,
                confidenceScore = snapshot.confidenceScore,
                precision = snapshot.precision.name,
                sourceSignalsCsv = snapshot.sourceSignals.joinToString(separator = ","),
                batteryLevelPercent = snapshot.batteryLevelPercent,
                networkType = snapshot.networkType.name,
                motionState = snapshot.motionState.name,
                hashedWifiSsid = snapshot.hashedWifiSsid,
                hashedWifiBssid = snapshot.hashedWifiBssid,
                geofenceTransition = snapshot.geofenceTransition,
                wifiRttCapable = snapshot.wifiRttCapable,
                suspiciousMockLocation = snapshot.suspiciousMockLocation,
                spoofingReasonsCsv = snapshot.spoofingReasons.joinToString(separator = ",")
            )
        )
        return snapshot
    }

    private fun LocationSampleEntity.toDomain(): LocationSnapshot {
        return LocationSnapshot(
            latitude = latitude,
            longitude = longitude,
            accuracyMeters = accuracyMeters,
            capturedAtEpochMs = capturedAtEpochMs,
            source = source,
            methodLabel = methodLabel,
            isApproximate = isApproximate,
            confidenceScore = confidenceScore,
            precision = enumValueOrDefault(precision, LocationPrecision.MODERATE),
            sourceSignals = sourceSignalsCsv.toCsvList(),
            batteryLevelPercent = batteryLevelPercent,
            networkType = enumValueOrDefault(networkType, NetworkType.UNKNOWN),
            motionState = enumValueOrDefault(motionState, MotionState.UNKNOWN),
            hashedWifiSsid = hashedWifiSsid,
            hashedWifiBssid = hashedWifiBssid,
            geofenceTransition = geofenceTransition,
            wifiRttCapable = wifiRttCapable,
            suspiciousMockLocation = suspiciousMockLocation,
            spoofingReasons = spoofingReasonsCsv.toCsvList()
        )
    }

    private fun String?.toCsvList(): List<String> {
        if (this.isNullOrBlank()) return emptyList()
        return split(",")
            .map { it.trim() }
            .filter { it.isNotEmpty() }
    }

    private inline fun <reified T : Enum<T>> enumValueOrDefault(raw: String, fallback: T): T {
        return runCatching { enumValueOf<T>(raw) }.getOrDefault(fallback)
    }
}
