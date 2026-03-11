package com.example.trackme.feature.incidents

import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.model.IncidentState
import com.example.trackme.domain.model.IncidentTimelineEntry

data class IncidentsContent(
    val incidentId: String? = null,
    val incidentState: IncidentState = IncidentState.NORMAL,
    val ticketReference: String = "",
    val recoveryMessage: String = "",
    val wipeReason: String = "",
    val wipeDelayMinutes: String = "60",
    val elevatedConfirmationText: String = "",
    val acknowledgedWipeTradeoff: Boolean = false,
    val confirmedWipeIntent: Boolean = false,
    val lostModeUntilEpochMs: Long? = null,
    val wipeScheduledAtEpochMs: Long? = null,
    val timeline: List<IncidentTimelineEntry> = emptyList(),
    val statusMessage: String? = null,
    val inProgress: Boolean = false
)

typealias IncidentsUiState = AsyncUiState<IncidentsContent>
