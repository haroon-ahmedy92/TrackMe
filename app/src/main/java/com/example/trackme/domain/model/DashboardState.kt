package com.example.trackme.domain.model

import com.example.trackme.trust.DeviceTrustSummary

data class DashboardState(
    val enrollment: EnrollmentStatus,
    val deviceState: DeviceState,
    val lastLocation: LocationSnapshot?,
    val trustSummary: DeviceTrustSummary,
)
