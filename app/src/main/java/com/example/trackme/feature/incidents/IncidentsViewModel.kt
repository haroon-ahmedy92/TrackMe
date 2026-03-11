package com.example.trackme.feature.incidents

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.usecase.ManageIncidentLifecycleUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

@HiltViewModel
class IncidentsViewModel @Inject constructor(
    private val manageIncidentLifecycleUseCase: ManageIncidentLifecycleUseCase
) : ViewModel() {
    private val _uiState = MutableStateFlow<IncidentsUiState>(AsyncUiState.Data(IncidentsContent()))
    val uiState: StateFlow<IncidentsUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            combine(
                manageIncidentLifecycleUseCase.observeCurrentIncident(),
                manageIncidentLifecycleUseCase.observeTimeline()
            ) { incident, timeline ->
                incident to timeline
            }.collect { (incident, timeline) ->
                update { current ->
                    current.copy(
                        incidentId = incident.incidentId,
                        incidentState = incident.state,
                        ticketReference = if (current.ticketReference.isBlank()) {
                            incident.ticketReference
                        } else {
                            current.ticketReference
                        },
                        recoveryMessage = if (current.recoveryMessage.isBlank()) {
                            incident.recoveryMessage.orEmpty()
                        } else {
                            current.recoveryMessage
                        },
                        lostModeUntilEpochMs = incident.lostModeUntilEpochMs,
                        wipeScheduledAtEpochMs = incident.wipeScheduledAtEpochMs,
                        timeline = timeline
                    )
                }
            }
        }
    }

    fun onTicketChanged(value: String) = update { it.copy(ticketReference = value) }
    fun onRecoveryMessageChanged(value: String) = update { it.copy(recoveryMessage = value) }
    fun onWipeReasonChanged(value: String) = update { it.copy(wipeReason = value) }
    fun onWipeDelayChanged(value: String) = update { it.copy(wipeDelayMinutes = value) }
    fun onElevatedConfirmationChanged(value: String) = update { it.copy(elevatedConfirmationText = value) }
    fun onAcknowledgeTradeoffChanged(value: Boolean) = update { it.copy(acknowledgedWipeTradeoff = value) }
    fun onConfirmWipeIntentChanged(value: Boolean) = update { it.copy(confirmedWipeIntent = value) }

    fun markAsLost() = runAction(successMessage = "Incident marked as suspected lost") {
        val content = currentContent()
        manageIncidentLifecycleUseCase.markAsLost(
            ticketReference = content.ticketReference,
            recoveryMessage = content.recoveryMessage
        ).getOrThrow()
    }

    fun confirmStolen() = runAction(successMessage = "Incident confirmed stolen") {
        val content = currentContent()
        manageIncidentLifecycleUseCase.confirmStolen(
            elevatedConfirmationText = content.elevatedConfirmationText,
            reason = "Elevated confirmation from visible incident workflow"
        ).getOrThrow()
    }

    fun requestRemoteLock() {
        runAction(successMessage = "Remote lock decision submitted") {
            val content = currentContent()
            manageIncidentLifecycleUseCase.requestRemoteLock(
                reason = content.wipeReason.ifBlank { "Remote lock requested from incidents screen" }
            ).getOrThrow()
        }
    }

    fun requestRemoteWipe() {
        runAction(successMessage = "Remote wipe workflow updated") {
            val content = currentContent()
            val delay = content.wipeDelayMinutes.trim().toIntOrNull()
                ?: throw IllegalArgumentException("Delayed wipe minutes must be a number.")
            manageIncidentLifecycleUseCase.requestOrScheduleRemoteWipe(
                reason = content.wipeReason,
                delayMinutes = delay,
                elevatedConfirmationText = content.elevatedConfirmationText,
                acknowledgedTradeoff = content.acknowledgedWipeTradeoff,
                confirmedWipeIntent = content.confirmedWipeIntent
            ).getOrThrow()
        }
    }

    fun recover() = runAction(successMessage = "Incident marked recovered") {
        val content = currentContent()
        manageIncidentLifecycleUseCase.recover(
            reason = content.wipeReason.ifBlank { "Recovered by operator" }
        ).getOrThrow()
    }

    fun cancelIncident() = runAction(successMessage = "Incident cancelled") {
        val content = currentContent()
        manageIncidentLifecycleUseCase.cancel(
            reason = content.wipeReason.ifBlank { "Cancelled by operator" }
        ).getOrThrow()
    }

    fun decommission() = runAction(successMessage = "Device decommissioned") {
        val content = currentContent()
        manageIncidentLifecycleUseCase.decommission(
            reason = content.wipeReason.ifBlank { "Decommissioned by operator" }
        ).getOrThrow()
    }

    private fun runAction(successMessage: String, block: suspend () -> Unit) {
        viewModelScope.launch {
            update { it.copy(inProgress = true, statusMessage = null) }
            runCatching { block() }
                .onSuccess { update { it.copy(inProgress = false, statusMessage = successMessage) } }
                .onFailure { throwable ->
                    update {
                        it.copy(
                            inProgress = false,
                            statusMessage = throwable.message ?: "Action failed"
                        )
                    }
                }
        }
    }

    private fun currentContent(): IncidentsContent {
        return (_uiState.value as? AsyncUiState.Data)?.value ?: IncidentsContent()
    }

    private fun update(transform: (IncidentsContent) -> IncidentsContent) {
        val state = _uiState.value
        if (state is AsyncUiState.Data) {
            _uiState.update { AsyncUiState.Data(transform(state.value)) }
        }
    }
}
