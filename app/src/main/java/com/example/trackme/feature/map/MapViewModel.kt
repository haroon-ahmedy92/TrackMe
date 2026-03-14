package com.example.trackme.feature.map

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.repository.LocationRepository
import com.example.trackme.domain.usecase.ObserveDashboardStateUseCase
import com.example.trackme.ui.map.MapProvider
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch

@HiltViewModel
class MapViewModel @Inject constructor(
    private val observeDashboardStateUseCase: ObserveDashboardStateUseCase,
    private val locationRepository: LocationRepository,
    val mapProvider: MapProvider
) : ViewModel() {

    private val _uiState = MutableStateFlow<MapUiState>(AsyncUiState.Loading)
    val uiState: StateFlow<MapUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            combine(
                observeDashboardStateUseCase(),
                locationRepository.observeRecentHistory(limit = 24)
            ) { dashboard, history ->
                MapContentState(
                    dashboard = dashboard,
                    history = history
                )
            }.collect {
                _uiState.value = AsyncUiState.Data(it)
            }
        }
    }
}
