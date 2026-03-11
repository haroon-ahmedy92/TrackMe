package com.example.trackme.feature.status

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.usecase.ObserveDashboardStateUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

@HiltViewModel
class DeviceStatusViewModel @Inject constructor(
    private val observeDashboardStateUseCase: ObserveDashboardStateUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow<DeviceStatusUiState>(AsyncUiState.Loading)
    val uiState: StateFlow<DeviceStatusUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            observeDashboardStateUseCase().collect {
                _uiState.value = AsyncUiState.Data(it)
            }
        }
    }
}
