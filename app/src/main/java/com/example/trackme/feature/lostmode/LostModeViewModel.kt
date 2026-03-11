package com.example.trackme.feature.lostmode

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.trackme.core.TimeProvider
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.usecase.ObserveDashboardStateUseCase
import com.example.trackme.domain.usecase.SetLostModeUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

@HiltViewModel
class LostModeViewModel @Inject constructor(
    observeDashboardStateUseCase: ObserveDashboardStateUseCase,
    private val setLostModeUseCase: SetLostModeUseCase,
    private val timeProvider: TimeProvider
) : ViewModel() {

    private val _uiState = MutableStateFlow<LostModeUiState>(AsyncUiState.Data(LostModeContent()))
    val uiState: StateFlow<LostModeUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            observeDashboardStateUseCase().collect { dashboard ->
                val until = dashboard.deviceState.lostModeUntilEpochMs
                val current = (_uiState.value as? AsyncUiState.Data)?.value ?: LostModeContent()
                _uiState.value = AsyncUiState.Data(
                    current.copy(
                        enabled = until != null,
                        untilEpochMs = until
                    )
                )
            }
        }
    }

    fun enable(hours: Int) {
        val untilEpochMs = timeProvider.nowEpochMillis() + hours * HOUR_MILLIS
        runAction {
            setLostModeUseCase.enable(untilEpochMs)
        }
    }

    fun disable() {
        runAction {
            setLostModeUseCase.disable()
        }
    }

    private fun runAction(block: suspend () -> Unit) {
        val current = (_uiState.value as? AsyncUiState.Data)?.value ?: LostModeContent()
        _uiState.value = AsyncUiState.Data(current.copy(inProgress = true, errorMessage = null))
        viewModelScope.launch {
            runCatching { block() }
                .onFailure { throwable ->
                    _uiState.update {
                        val data = (it as? AsyncUiState.Data)?.value ?: LostModeContent()
                        AsyncUiState.Data(
                            data.copy(
                                inProgress = false,
                                errorMessage = throwable.message ?: "Action failed"
                            )
                        )
                    }
                }
                .onSuccess {
                    _uiState.update {
                        val data = (it as? AsyncUiState.Data)?.value ?: LostModeContent()
                        AsyncUiState.Data(data.copy(inProgress = false))
                    }
                }
        }
    }

    companion object {
        private const val HOUR_MILLIS = 60 * 60 * 1000L
    }
}
