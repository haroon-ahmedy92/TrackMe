package com.example.trackme.feature.lostmode

import com.example.trackme.core.ui.AsyncUiState

data class LostModeContent(
    val enabled: Boolean = false,
    val untilEpochMs: Long? = null,
    val inProgress: Boolean = false,
    val errorMessage: String? = null
)

typealias LostModeUiState = AsyncUiState<LostModeContent>
