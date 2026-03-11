package com.example.trackme.ui

sealed class AppDestination(val route: String, val label: String) {
    data object Enrollment : AppDestination("enrollment", "Enrollment")
    data object Dashboard : AppDestination("dashboard", "Dashboard")
    data object LostMode : AppDestination("lost_mode", "Lost Mode")
    data object Audit : AppDestination("audit", "Audit")
}
