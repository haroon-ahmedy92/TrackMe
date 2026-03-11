package com.example.trackme.feature.settings

import com.example.trackme.core.ui.AsyncUiState

data class SettingsContent(
    val geofenceEnabled: Boolean = false,
    val geofenceRadiusMeters: Int = 250,
    val statusMessage: String? = null
)

typealias SettingsUiState = AsyncUiState<SettingsContent>
