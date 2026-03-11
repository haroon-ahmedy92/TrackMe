package com.example.trackme.location

import javax.inject.Inject

/**
 * Optional approximate location signal sourced from backend/network intelligence.
 * This intentionally returns coarse estimates and is always labelled approximate.
 */
interface IpApproximateLocationProvider {
    suspend fun estimateApproximateLocation(): IpApproximateLocation?
}

data class IpApproximateLocation(
    val latitude: Double,
    val longitude: Double,
    val accuracyMeters: Float
)

class NoopIpApproximateLocationProvider @Inject constructor() : IpApproximateLocationProvider {
    override suspend fun estimateApproximateLocation(): IpApproximateLocation? = null
}
