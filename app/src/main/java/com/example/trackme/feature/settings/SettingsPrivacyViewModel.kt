package com.example.trackme.feature.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.data.preferences.TrackingPreferencesDataSource
import com.example.trackme.domain.repository.AuditRepository
import com.example.trackme.domain.repository.GeofenceRepository
import com.example.trackme.domain.usecase.SetGeofenceProtectionUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

@HiltViewModel
class SettingsPrivacyViewModel @Inject constructor(
    private val geofenceRepository: GeofenceRepository,
    private val setGeofenceProtectionUseCase: SetGeofenceProtectionUseCase,
    private val trackingPreferences: TrackingPreferencesDataSource,
    private val auditRepository: AuditRepository,
) : ViewModel() {

    private val statusMessage = MutableStateFlow<String?>(null)

    val uiState: StateFlow<SettingsUiState> = combine(
        geofenceRepository.observeConfig(),
        trackingPreferences.explicitTrackingConsentVersion,
        trackingPreferences.explicitTrackingConsentAtEpochMs,
        auditRepository.observeRecentEvents(limit = 40),
        statusMessage,
    ) { config, consentVersion, consentAt, auditEvents, message ->
        AsyncUiState.Data(
            SettingsContent(
                geofenceEnabled = config.enabled,
                geofenceRadiusMeters = config.radiusMeters,
                consentVersion = consentVersion,
                consentAcceptedAtEpochMs = consentAt,
                accessHistory = auditEvents
                    .filter {
                        it.type.contains("CONSENT") ||
                            it.type.contains("LOCATION_LOOKUP") ||
                            it.type.contains("DEPROVISION") ||
                            it.type.contains("ABUSE_REPORT") ||
                            it.type.contains("ENROLL")
                    }
                    .take(8)
                    .map {
                        SettingsAccessHistoryItem(
                            id = it.id,
                            title = it.type
                                .replace('_', ' ')
                                .lowercase()
                                .split(' ')
                                .joinToString(" ") { part -> part.replaceFirstChar(Char::uppercaseChar) },
                            summary = it.summary,
                            createdAtEpochMs = it.createdAtEpochMs
                        )
                    },
                statusMessage = message
            )
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), AsyncUiState.Loading)

    fun onGeofenceToggle(enabled: Boolean) {
        val current = (uiState.value as? AsyncUiState.Data)?.value ?: return
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
        val current = (uiState.value as? AsyncUiState.Data)?.value ?: return
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

    fun submitAbuseReport(description: String) {
        viewModelScope.launch {
            runCatching {
                auditRepository.appendEvent(
                    type = "ABUSE_REPORT_SUBMITTED",
                    summary = "User submitted an abuse or misuse concern",
                    metadata = mapOf("description" to description.take(300))
                )
            }.onSuccess {
                setMessage("Abuse report recorded in the local audit trail")
            }.onFailure {
                setMessage(it.message ?: "Failed to record abuse report")
            }
        }
    }

    fun requestDeprovision(reason: String) {
        viewModelScope.launch {
            runCatching {
                auditRepository.appendEvent(
                    type = "DEPROVISION_REQUESTED",
                    summary = "Device owner/admin requested deprovision",
                    metadata = mapOf("reason" to reason.take(280))
                )
            }.onSuccess {
                setMessage("Deprovision request recorded. Final removal should be completed by an authorized admin workflow.")
            }.onFailure {
                setMessage(it.message ?: "Failed to record deprovision request")
            }
        }
    }

    private fun setMessage(message: String) {
        statusMessage.value = message
    }
}
