package com.example.trackme.app

sealed class AppDestination(val route: String) {
    data object Onboarding : AppDestination("onboarding")
    data object Enrollment : AppDestination("enrollment")
    data object Home : AppDestination("home")
    data object DeviceStatus : AppDestination("device_status")
    data object LostMode : AppDestination("lost_mode")
    data object Map : AppDestination("map")
    data object Incidents : AppDestination("incidents")
    data object Settings : AppDestination("settings")
    data object Audit : AppDestination("audit")
}
