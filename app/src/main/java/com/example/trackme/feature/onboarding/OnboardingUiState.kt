package com.example.trackme.feature.onboarding

import com.example.trackme.core.ui.AsyncUiState

data class OnboardingContent(
    val consentAccepted: Boolean = false,
    val foregroundLocationGranted: Boolean = false,
    val backgroundLocationGranted: Boolean = false,
    val backgroundDecisionMade: Boolean = false
)

typealias OnboardingUiState = AsyncUiState<OnboardingContent>
