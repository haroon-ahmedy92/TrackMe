package com.example.trackme.feature.onboarding

import androidx.lifecycle.ViewModel
import com.example.trackme.core.ui.AsyncUiState
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

@HiltViewModel
class OnboardingViewModel @Inject constructor() : ViewModel() {

    private val _uiState = MutableStateFlow<OnboardingUiState>(AsyncUiState.Data(OnboardingContent()))
    val uiState: StateFlow<OnboardingUiState> = _uiState.asStateFlow()

    fun setConsentAccepted(accepted: Boolean) {
        updateContent { it.copy(consentAccepted = accepted) }
    }

    fun setForegroundPermission(granted: Boolean) {
        updateContent { it.copy(foregroundLocationGranted = granted) }
    }

    fun refreshPermissions(foregroundGranted: Boolean, backgroundGranted: Boolean) {
        updateContent {
            it.copy(
                foregroundLocationGranted = foregroundGranted,
                backgroundLocationGranted = backgroundGranted
            )
        }
    }

    fun setBackgroundPermissionDecision(granted: Boolean) {
        updateContent {
            it.copy(
                backgroundLocationGranted = granted,
                backgroundDecisionMade = true
            )
        }
    }

    fun skipBackgroundPermission() {
        updateContent { it.copy(backgroundDecisionMade = true, backgroundLocationGranted = false) }
    }

    private fun updateContent(transform: (OnboardingContent) -> OnboardingContent) {
        val current = _uiState.value
        if (current is AsyncUiState.Data) {
            _uiState.update { AsyncUiState.Data(transform(current.value)) }
        }
    }
}
