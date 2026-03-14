package com.example.trackme.data.preferences

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.trackingDataStore: DataStore<Preferences> by preferencesDataStore(name = "tracking_preferences")

@Singleton
class TrackingPreferencesDataSource @Inject constructor(
    @ApplicationContext private val context: Context
) {
    val normalIntervalMinutes: Flow<Long> = context.trackingDataStore.data.map {
        it[NORMAL_INTERVAL_MINUTES] ?: DEFAULT_NORMAL_INTERVAL_MINUTES
    }

    val lostModeIntervalMinutes: Flow<Long> = context.trackingDataStore.data.map {
        it[LOST_INTERVAL_MINUTES] ?: DEFAULT_LOST_INTERVAL_MINUTES
    }

    val misplacedIntervalMinutes: Flow<Long> = context.trackingDataStore.data.map {
        it[MISPLACED_INTERVAL_MINUTES] ?: DEFAULT_MISPLACED_INTERVAL_MINUTES
    }

    val geofenceProtectionEnabled: Flow<Boolean> = context.trackingDataStore.data.map {
        it[GEOFENCE_ENABLED] ?: DEFAULT_GEOFENCE_ENABLED
    }

    val geofenceRadiusMeters: Flow<Int> = context.trackingDataStore.data.map {
        it[GEOFENCE_RADIUS_METERS] ?: DEFAULT_GEOFENCE_RADIUS_METERS
    }

    val explicitTrackingConsentGranted: Flow<Boolean> = context.trackingDataStore.data.map {
        it[EXPLICIT_TRACKING_CONSENT_GRANTED] ?: false
    }

    val explicitTrackingConsentVersion: Flow<String?> = context.trackingDataStore.data.map {
        it[EXPLICIT_TRACKING_CONSENT_VERSION]
    }

    val explicitTrackingConsentAtEpochMs: Flow<Long?> = context.trackingDataStore.data.map {
        it[EXPLICIT_TRACKING_CONSENT_AT_EPOCH_MS]
    }

    suspend fun setIntervals(normalMinutes: Long, misplacedMinutes: Long, lostMinutes: Long) {
        context.trackingDataStore.edit {
            it[NORMAL_INTERVAL_MINUTES] = normalMinutes
            it[MISPLACED_INTERVAL_MINUTES] = misplacedMinutes
            it[LOST_INTERVAL_MINUTES] = lostMinutes
        }
    }

    suspend fun setGeofenceProtection(enabled: Boolean, radiusMeters: Int) {
        context.trackingDataStore.edit {
            it[GEOFENCE_ENABLED] = enabled
            it[GEOFENCE_RADIUS_METERS] = radiusMeters
        }
    }

    suspend fun grantExplicitTrackingConsent(consentVersion: String, acceptedAtEpochMs: Long) {
        context.trackingDataStore.edit {
            it[EXPLICIT_TRACKING_CONSENT_GRANTED] = true
            it[EXPLICIT_TRACKING_CONSENT_VERSION] = consentVersion
            it[EXPLICIT_TRACKING_CONSENT_AT_EPOCH_MS] = acceptedAtEpochMs
        }
    }

    suspend fun revokeExplicitTrackingConsent() {
        context.trackingDataStore.edit {
            it[EXPLICIT_TRACKING_CONSENT_GRANTED] = false
            it.remove(EXPLICIT_TRACKING_CONSENT_VERSION)
            it.remove(EXPLICIT_TRACKING_CONSENT_AT_EPOCH_MS)
        }
    }

    companion object {
        private val NORMAL_INTERVAL_MINUTES = longPreferencesKey("normal_interval_minutes")
        private val MISPLACED_INTERVAL_MINUTES = longPreferencesKey("misplaced_interval_minutes")
        private val LOST_INTERVAL_MINUTES = longPreferencesKey("lost_interval_minutes")
        private val GEOFENCE_ENABLED = booleanPreferencesKey("geofence_enabled")
        private val GEOFENCE_RADIUS_METERS = intPreferencesKey("geofence_radius_meters")
        private val EXPLICIT_TRACKING_CONSENT_GRANTED =
            booleanPreferencesKey("explicit_tracking_consent_granted")
        private val EXPLICIT_TRACKING_CONSENT_VERSION =
            stringPreferencesKey("explicit_tracking_consent_version")
        private val EXPLICIT_TRACKING_CONSENT_AT_EPOCH_MS =
            longPreferencesKey("explicit_tracking_consent_at_epoch_ms")

        const val DEFAULT_NORMAL_INTERVAL_MINUTES = 120L
        const val DEFAULT_MISPLACED_INTERVAL_MINUTES = 60L
        const val DEFAULT_LOST_INTERVAL_MINUTES = 15L
        const val DEFAULT_GEOFENCE_ENABLED = false
        const val DEFAULT_GEOFENCE_RADIUS_METERS = 250
    }
}
