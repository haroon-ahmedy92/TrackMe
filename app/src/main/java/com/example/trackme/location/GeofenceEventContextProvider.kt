package com.example.trackme.location

import com.example.trackme.core.TimeProvider
import java.util.concurrent.atomic.AtomicReference
import javax.inject.Inject
import javax.inject.Singleton

data class GeofenceEventContext(
    val transition: String,
    val occurredAtEpochMs: Long
)

interface GeofenceEventContextProvider {
    suspend fun latestEvent(maxAgeMs: Long): GeofenceEventContext?
}

@Singleton
class InMemoryGeofenceEventContextProvider @Inject constructor(
    private val timeProvider: TimeProvider
) : GeofenceEventContextProvider {

    private val latest = AtomicReference<GeofenceEventContext?>(null)

    override suspend fun latestEvent(maxAgeMs: Long): GeofenceEventContext? {
        val event = latest.get() ?: return null
        val ageMs = (timeProvider.nowEpochMillis() - event.occurredAtEpochMs).coerceAtLeast(0L)
        return event.takeIf { ageMs <= maxAgeMs }
    }

    /**
     * Hook for a future Geofence BroadcastReceiver/worker pipeline.
     * Stores the latest visible geofence transition signal for fusion scoring.
     */
    fun record(transition: String, occurredAtEpochMs: Long = timeProvider.nowEpochMillis()) {
        latest.set(
            GeofenceEventContext(
                transition = transition,
                occurredAtEpochMs = occurredAtEpochMs
            )
        )
    }
}
