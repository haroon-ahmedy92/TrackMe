package com.example.trackme.domain.model

data class DashboardState(
    val enrollment: EnrollmentStatus,
    val deviceState: DeviceState,
    val lastLocation: LocationSnapshot?
)
