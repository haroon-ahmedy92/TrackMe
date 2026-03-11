package com.example.trackme.domain.model

data class DeviceState(
    val mode: CheckInMode,
    val lastCheckInEpochMs: Long?,
    val batteryPercent: Int?,
    val lostModeUntilEpochMs: Long?
)
