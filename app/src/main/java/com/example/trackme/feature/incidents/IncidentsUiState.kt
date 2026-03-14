package com.example.trackme.feature.incidents

import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.model.DeviceCommand
import com.example.trackme.domain.model.IncidentAttachmentReference
import com.example.trackme.domain.model.IncidentCaseNote
import com.example.trackme.domain.model.IncidentEvidenceExport
import com.example.trackme.domain.model.IncidentState
import com.example.trackme.domain.model.IncidentTimelineEntry
import com.example.trackme.domain.model.LocationSnapshot

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
    val notes: List<IncidentCaseNote> = emptyList(),
    val attachments: List<IncidentAttachmentReference> = emptyList(),
    val evidenceExports: List<IncidentEvidenceExport> = emptyList(),
    val actionsTaken: List<DeviceCommand> = emptyList(),
    val lastKnownLocation: LocationSnapshot? = null,
    val evidenceChain: List<IncidentCaseEntry> = emptyList(),
    val noteDraft: String = "",
    val notePinned: Boolean = false,
    val attachmentNameDraft: String = "",
    val attachmentDescriptionDraft: String = "",
    val statusMessage: String? = null,
    val inProgress: Boolean = false
)

typealias IncidentsUiState = AsyncUiState<IncidentsContent>
