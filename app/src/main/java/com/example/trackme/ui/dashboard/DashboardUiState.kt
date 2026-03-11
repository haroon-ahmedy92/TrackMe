package com.example.trackme.ui.dashboard

import com.example.trackme.domain.model.DashboardState

data class DashboardUiState(
    val isLoading: Boolean = true,
    val dashboardState: DashboardState? = null
)
