package com.example.trackme.feature.settings

import com.example.trackme.core.ui.AsyncUiState

data class SettingsAccessHistoryItem(
    val id: Long,
    val title: String,
    val summary: String,
    val createdAtEpochMs: Long
)

data class SettingsContent(
    val geofenceEnabled: Boolean = false,
    val geofenceRadiusMeters: Int = 250,
    val consentVersion: String? = null,
    val consentAcceptedAtEpochMs: Long? = null,
    val accessHistory: List<SettingsAccessHistoryItem> = emptyList(),
    val statusMessage: String? = null
)

typealias SettingsUiState = AsyncUiState<SettingsContent>
