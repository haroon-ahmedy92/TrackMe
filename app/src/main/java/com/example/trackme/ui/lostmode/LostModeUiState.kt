package com.example.trackme.ui.lostmode

data class LostModeUiState(
    val isEnabled: Boolean = false,
    val lostModeUntilEpochMs: Long? = null,
    val isUpdating: Boolean = false,
    val errorMessage: String? = null
)
