package com.example.trackme.feature.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.repository.GeofenceRepository
import com.example.trackme.domain.usecase.SetGeofenceProtectionUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

@HiltViewModel
class SettingsPrivacyViewModel @Inject constructor(
    private val geofenceRepository: GeofenceRepository,
    private val setGeofenceProtectionUseCase: SetGeofenceProtectionUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow<SettingsUiState>(AsyncUiState.Loading)
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            geofenceRepository.observeConfig().collect { config ->
                val oldMessage = (_uiState.value as? AsyncUiState.Data)?.value?.statusMessage
                _uiState.value = AsyncUiState.Data(
                    SettingsContent(
                        geofenceEnabled = config.enabled,
                        geofenceRadiusMeters = config.radiusMeters,
                        statusMessage = oldMessage
                    )
                )
            }
        }
    }

    fun onGeofenceToggle(enabled: Boolean) {
        val current = (_uiState.value as? AsyncUiState.Data)?.value ?: return
        viewModelScope.launch {
            runCatching {
                setGeofenceProtectionUseCase(enabled = enabled, radiusMeters = current.geofenceRadiusMeters)
            }.onSuccess {
                setMessage("Geofence updated")
            }.onFailure {
                setMessage(it.message ?: "Failed to update geofence")
            }
        }
    }

    fun onRadiusChange(radius: Int) {
        val current = (_uiState.value as? AsyncUiState.Data)?.value ?: return
        viewModelScope.launch {
            runCatching {
                setGeofenceProtectionUseCase(enabled = current.geofenceEnabled, radiusMeters = radius)
            }.onSuccess {
                setMessage("Radius updated")
            }.onFailure {
                setMessage(it.message ?: "Failed to update radius")
            }
        }
    }

    private fun setMessage(message: String) {
        val state = _uiState.value
        if (state is AsyncUiState.Data) {
            _uiState.update { AsyncUiState.Data(state.value.copy(statusMessage = message)) }
        }
    }
}
