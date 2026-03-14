package com.example.trackme.feature.onboarding

import com.example.trackme.compliance.ConsentDisclosure
import com.example.trackme.core.ui.AsyncUiState

data class OnboardingContent(
    val disclosure: ConsentDisclosure? = null,
    val consentAccepted: Boolean = false,
    val foregroundLocationGranted: Boolean = false,
    val backgroundLocationGranted: Boolean = false,
    val backgroundDecisionMade: Boolean = false
)

typealias OnboardingUiState = AsyncUiState<OnboardingContent>
