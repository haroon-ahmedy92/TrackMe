package com.example.trackme.ui.lostmode

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.trackme.core.TimeProvider
import com.example.trackme.domain.usecase.ObserveDashboardStateUseCase
import com.example.trackme.domain.usecase.SetLostModeUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class LostModeViewModel @Inject constructor(
    observeDashboardStateUseCase: ObserveDashboardStateUseCase,
    private val setLostModeUseCase: SetLostModeUseCase,
    private val timeProvider: TimeProvider
) : ViewModel() {

    private val _uiState = MutableStateFlow(LostModeUiState())
    val uiState: StateFlow<LostModeUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            observeDashboardStateUseCase().collect { dashboard ->
                val until = dashboard.deviceState.lostModeUntilEpochMs
                _uiState.update {
                    it.copy(
                        isEnabled = until != null,
                        lostModeUntilEpochMs = until
                    )
                }
            }
        }
    }

    fun enable(hours: Int) {
        val until = timeProvider.nowEpochMillis() + hours * HOUR_IN_MILLIS
        viewModelScope.launch {
            _uiState.update { it.copy(isUpdating = true, errorMessage = null) }
            runCatching {
                setLostModeUseCase.enable(until)
            }.onFailure { throwable ->
                _uiState.update {
                    it.copy(isUpdating = false, errorMessage = throwable.message ?: "Failed to enable lost mode")
                }
            }.onSuccess {
                _uiState.update { it.copy(isUpdating = false) }
            }
        }
    }

    fun disable() {
        viewModelScope.launch {
            _uiState.update { it.copy(isUpdating = true, errorMessage = null) }
            runCatching {
                setLostModeUseCase.disable()
            }.onFailure { throwable ->
                _uiState.update {
                    it.copy(isUpdating = false, errorMessage = throwable.message ?: "Failed to disable lost mode")
                }
            }.onSuccess {
                _uiState.update { it.copy(isUpdating = false) }
            }
        }
    }

    companion object {
        private const val HOUR_IN_MILLIS = 60 * 60 * 1000L
    }
}
