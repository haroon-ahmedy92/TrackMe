package com.example.trackme.data.repository

import com.example.trackme.data.local.dao.LocationDao
import com.example.trackme.data.local.entity.LocationSampleEntity
import com.example.trackme.domain.model.LocationPrecision
import com.example.trackme.domain.model.LocationSnapshot
import com.example.trackme.location.DeviceLocationProvider
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Test

class LocationRepositoryImplTest {

    @Test
    fun observeRecentHistory_returnsOldestFirstForPlayback() = runTest {
        val dao = FakeLocationDao()
        dao.recent.value = listOf(
            sample(id = 2, capturedAtEpochMs = 2_000L, latitude = -6.7924, longitude = 39.2083),
            sample(id = 1, capturedAtEpochMs = 1_000L, latitude = -6.7930, longitude = 39.2079),
        )
        val repository = LocationRepositoryImpl(
            locationDao = dao,
            locationProvider = FakeDeviceLocationProvider()
        )

        val history = repository.observeRecentHistory(limit = 10).first()

        assertEquals(listOf(1_000L, 2_000L), history.map { it.capturedAtEpochMs })
    }
}

private class FakeLocationDao : LocationDao {
    val latest = MutableStateFlow<LocationSampleEntity?>(null)
    val recent = MutableStateFlow<List<LocationSampleEntity>>(emptyList())

    override suspend fun insert(entity: LocationSampleEntity) = Unit

    override fun observeLatest(): Flow<LocationSampleEntity?> = latest

    override fun observeRecent(limit: Int): Flow<List<LocationSampleEntity>> = recent
}

private class FakeDeviceLocationProvider : DeviceLocationProvider {
    override suspend fun getCurrentLocation(source: String): LocationSnapshot? = null
}

private fun sample(
    id: Long,
    capturedAtEpochMs: Long,
    latitude: Double,
    longitude: Double
) = LocationSampleEntity(
    id = id,
    latitude = latitude,
    longitude = longitude,
    accuracyMeters = 18f,
    capturedAtEpochMs = capturedAtEpochMs,
    source = "test",
    methodLabel = "Fused GPS",
    isApproximate = false,
    confidenceScore = 85,
    precision = LocationPrecision.PRECISE.name,
    sourceSignalsCsv = "fused_gps",
    batteryLevelPercent = 75,
    networkType = "WIFI",
    motionState = "STILL",
    hashedWifiSsid = null,
    hashedWifiBssid = null,
    geofenceTransition = null,
    wifiRttCapable = false,
    suspiciousMockLocation = false,
    spoofingReasonsCsv = ""
)
