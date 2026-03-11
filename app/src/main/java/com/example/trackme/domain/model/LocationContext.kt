package com.example.trackme.domain.model

enum class LocationPrecision {
    PRECISE,
    MODERATE,
    APPROXIMATE
}

enum class MotionState {
    STILL,
    ON_FOOT,
    IN_VEHICLE,
    UNKNOWN
}

enum class NetworkType {
    WIFI,
    CELLULAR,
    ETHERNET,
    NONE,
    UNKNOWN
}
