package com.example.trackme.feature.common

import com.example.trackme.domain.model.LocationSnapshot
import com.example.trackme.domain.model.NetworkType

enum class LocationFreshness {
    RECENT,
    STALE,
    OFFLINE
}

fun LocationSnapshot.freshness(
    nowEpochMs: Long = System.currentTimeMillis(),
    staleAfterMs: Long = 30 * 60 * 1000L,
): LocationFreshness = when {
    networkType == NetworkType.NONE -> LocationFreshness.OFFLINE
    nowEpochMs - capturedAtEpochMs > staleAfterMs -> LocationFreshness.STALE
    else -> LocationFreshness.RECENT
}
