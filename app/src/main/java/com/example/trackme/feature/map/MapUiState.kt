package com.example.trackme.feature.map

import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.model.DashboardState
import com.example.trackme.domain.model.LocationSnapshot

data class MapContentState(
    val dashboard: DashboardState,
    val history: List<LocationSnapshot>
)

typealias MapUiState = AsyncUiState<MapContentState>
