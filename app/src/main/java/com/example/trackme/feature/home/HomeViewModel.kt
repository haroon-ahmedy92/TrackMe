package com.example.trackme.feature.home

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
class HomeViewModel @Inject constructor(
    private val observeDashboardStateUseCase: ObserveDashboardStateUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow<HomeUiState>(AsyncUiState.Loading)
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            observeDashboardStateUseCase().collect {
                _uiState.value = AsyncUiState.Data(it)
            }
        }
    }
}
