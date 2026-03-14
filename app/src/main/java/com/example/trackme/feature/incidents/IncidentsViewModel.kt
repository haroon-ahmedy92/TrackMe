package com.example.trackme.feature.incidents

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.trackme.core.ui.AsyncUiState
import com.example.trackme.domain.model.DeviceCommand
import com.example.trackme.domain.model.IncidentAttachmentReference
import com.example.trackme.domain.model.IncidentCaseNote
import com.example.trackme.domain.model.IncidentEvidenceExport
import com.example.trackme.domain.model.IncidentEvidenceExportFormat
import com.example.trackme.domain.model.LocationSnapshot
import com.example.trackme.domain.repository.AuditRepository
import com.example.trackme.domain.repository.CommandRepository
import com.example.trackme.domain.repository.IncidentRepository
import com.example.trackme.domain.repository.LocationRepository
import com.example.trackme.domain.usecase.ManageIncidentLifecycleUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

@OptIn(ExperimentalCoroutinesApi::class)
@HiltViewModel
class IncidentsViewModel @Inject constructor(
    private val manageIncidentLifecycleUseCase: ManageIncidentLifecycleUseCase,
    private val incidentRepository: IncidentRepository,
    private val commandRepository: CommandRepository,
    private val locationRepository: LocationRepository,
    private val auditRepository: AuditRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow<IncidentsUiState>(AsyncUiState.Data(IncidentsContent()))
    val uiState: StateFlow<IncidentsUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            manageIncidentLifecycleUseCase.observeCurrentIncident()
                .flatMapLatest { incident ->
                    combine(
                        manageIncidentLifecycleUseCase.observeTimeline(),
                        incidentRepository.observeNotes(incident.incidentId.orEmpty()),
                        incidentRepository.observeAttachmentReferences(incident.incidentId.orEmpty()),
                        incidentRepository.observeEvidenceExports(incident.incidentId.orEmpty()),
                    ) { timeline, notes, attachments, evidenceExports ->
                        IncidentBaseBundle(
                            incident = incident,
                            timeline = timeline,
                            notes = notes,
                            attachments = attachments,
                            evidenceExports = evidenceExports,
                        )
                    }.let { baseFlow ->
                        combine(
                            baseFlow,
                            commandRepository.observeCommands(),
                            locationRepository.observeLastKnownLocation(),
                            auditRepository.observeRecentEvents(),
                        ) { base, commands, lastKnownLocation, auditEvents ->
                            IncidentPresentationBundle(
                                incident = base.incident,
                                timeline = base.timeline,
                                notes = base.notes,
                                attachments = base.attachments,
                                evidenceExports = base.evidenceExports,
                                commands = commands.filter { command ->
                                    base.incident.incidentId != null &&
                                        (command.incidentId == null || command.incidentId == base.incident.incidentId)
                                },
                                lastKnownLocation = lastKnownLocation,
                                evidenceChain = buildEvidenceChain(
                                    timeline = base.timeline,
                                    notes = base.notes,
                                    commands = commands,
                                    lastKnownLocation = lastKnownLocation,
                                    auditSummaries = auditEvents.map { it.summary to it.createdAtEpochMs },
                                    incidentId = base.incident.incidentId,
                                ),
                            )
                        }
                    }
                }
                .collect { bundle ->
                update { current ->
                    current.copy(
                        incidentId = bundle.incident.incidentId,
                        incidentState = bundle.incident.state,
                        ticketReference = if (current.ticketReference.isBlank()) {
                            bundle.incident.ticketReference
                        } else {
                            current.ticketReference
                        },
                        recoveryMessage = if (current.recoveryMessage.isBlank()) {
                            bundle.incident.recoveryMessage.orEmpty()
                        } else {
                            current.recoveryMessage
                        },
                        lostModeUntilEpochMs = bundle.incident.lostModeUntilEpochMs,
                        wipeScheduledAtEpochMs = bundle.incident.wipeScheduledAtEpochMs,
                        timeline = bundle.timeline,
                        notes = bundle.notes,
                        attachments = bundle.attachments,
                        evidenceExports = bundle.evidenceExports,
                        actionsTaken = bundle.commands.sortedByDescending { it.requestedAtEpochMs },
                        lastKnownLocation = bundle.lastKnownLocation,
                        evidenceChain = bundle.evidenceChain
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
    fun onNoteDraftChanged(value: String) = update { it.copy(noteDraft = value) }
    fun onNotePinnedChanged(value: Boolean) = update { it.copy(notePinned = value) }
    fun onAttachmentNameDraftChanged(value: String) = update { it.copy(attachmentNameDraft = value) }
    fun onAttachmentDescriptionDraftChanged(value: String) = update { it.copy(attachmentDescriptionDraft = value) }

    fun addCaseNote() {
        runAction(successMessage = "Case note saved locally") {
            val content = currentContent()
            val incidentId = content.incidentId ?: throw IllegalArgumentException("Open or create an incident first.")
            val body = content.noteDraft.trim()
            require(body.isNotBlank()) { "Case note cannot be empty." }
            val now = System.currentTimeMillis()
            incidentRepository.appendNote(
                IncidentCaseNote(
                    id = 0,
                    incidentId = incidentId,
                    authorLabel = DEFAULT_ACTOR_LABEL,
                    body = body,
                    isPinned = content.notePinned,
                    createdAtEpochMs = now,
                    updatedAtEpochMs = now
                )
            )
            auditRepository.appendEvent(
                type = "CASE_NOTE_CREATED",
                summary = "Mutable incident note added",
                metadata = mapOf("incidentId" to incidentId, "isPinned" to content.notePinned.toString())
            )
            update { it.copy(noteDraft = "", notePinned = false) }
        }
    }

    fun addAttachmentReference() {
        runAction(successMessage = "Attachment reference saved for this case") {
            val content = currentContent()
            val incidentId = content.incidentId ?: throw IllegalArgumentException("Open or create an incident first.")
            val fileName = content.attachmentNameDraft.trim()
            require(fileName.isNotBlank()) { "Attachment name is required." }
            incidentRepository.appendAttachmentReference(
                IncidentAttachmentReference(
                    id = 0,
                    incidentId = incidentId,
                    fileName = fileName,
                    description = content.attachmentDescriptionDraft.trim().ifBlank { null },
                    mediaType = "reference/placeholder",
                    byteSize = 0,
                    addedByLabel = DEFAULT_ACTOR_LABEL,
                    createdAtEpochMs = System.currentTimeMillis()
                )
            )
            auditRepository.appendEvent(
                type = "CASE_ATTACHMENT_RECORDED",
                summary = "Incident attachment metadata recorded",
                metadata = mapOf("incidentId" to incidentId, "fileName" to fileName)
            )
            update { it.copy(attachmentNameDraft = "", attachmentDescriptionDraft = "") }
        }
    }

    fun requestEvidenceExport(format: IncidentEvidenceExportFormat) {
        runAction(successMessage = "${format.name} export placeholder recorded") {
            val content = currentContent()
            val incidentId = content.incidentId ?: throw IllegalArgumentException("Open or create an incident first.")
            val redactionSummary = "Recommended redactions: latitude, longitude, owner identifiers"
            incidentRepository.appendEvidenceExport(
                IncidentEvidenceExport(
                    id = 0,
                    incidentId = incidentId,
                    format = format,
                    reason = "Visible export placeholder from Android incident view",
                    requestedByLabel = DEFAULT_ACTOR_LABEL,
                    redactionSummary = redactionSummary,
                    createdAtEpochMs = System.currentTimeMillis()
                )
            )
            auditRepository.appendEvent(
                type = "CASE_EVIDENCE_EXPORT_REQUESTED",
                summary = "Evidence export placeholder recorded",
                metadata = mapOf("incidentId" to incidentId, "format" to format.name)
            )
        }
    }

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

    private fun buildEvidenceChain(
        timeline: List<com.example.trackme.domain.model.IncidentTimelineEntry>,
        notes: List<IncidentCaseNote>,
        commands: List<DeviceCommand>,
        lastKnownLocation: LocationSnapshot?,
        auditSummaries: List<Pair<String, Long>>,
        incidentId: String?,
    ): List<IncidentCaseEntry> {
        val entries = mutableListOf<IncidentCaseEntry>()
        entries += timeline.map { event ->
            IncidentCaseEntry(
                id = "timeline-${event.id}",
                kind = IncidentCaseEntryKind.STATUS_CHANGE,
                title = event.action.replace('_', ' '),
                summary = event.summary,
                occurredAtEpochMs = event.createdAtEpochMs,
            )
        }
        lastKnownLocation?.let { location ->
            entries += IncidentCaseEntry(
                id = "location-${location.capturedAtEpochMs}",
                kind = IncidentCaseEntryKind.LOCATION,
                title = "Last known location",
                summary = buildString {
                    append(location.methodLabel)
                    append(" • ")
                    append("${location.confidenceScore}/100 confidence")
                    if (location.geofenceTransition != null) {
                        append(" • geofence ${location.geofenceTransition}")
                    }
                    if (location.isApproximate) {
                        append(" • approximate")
                    }
                },
                occurredAtEpochMs = location.capturedAtEpochMs,
            )
        }
        entries += commands
            .filter { incidentId == null || it.incidentId == null || it.incidentId == incidentId }
            .map { command ->
                IncidentCaseEntry(
                    id = "command-${command.commandId}",
                    kind = IncidentCaseEntryKind.COMMAND,
                    title = command.type.name.replace('_', ' '),
                    summary = "${command.status.name} • ${command.reason}",
                    occurredAtEpochMs = command.executedAtEpochMs ?: command.requestedAtEpochMs,
                    actorLabel = command.requestedBy,
                )
            }
        entries += notes.map { note ->
            IncidentCaseEntry(
                id = "note-${note.id}",
                kind = IncidentCaseEntryKind.NOTE,
                title = if (note.isPinned) "Pinned analyst note" else "Analyst note",
                summary = note.body,
                occurredAtEpochMs = note.updatedAtEpochMs,
                actorLabel = note.authorLabel,
                mutable = true,
            )
        }
        entries += auditSummaries.take(6).mapIndexed { index, (summary, createdAt) ->
            IncidentCaseEntry(
                id = "audit-$index-$createdAt",
                kind = IncidentCaseEntryKind.AUDIT,
                title = "Audit event",
                summary = summary,
                occurredAtEpochMs = createdAt,
            )
        }
        return entries.sortedByDescending { it.occurredAtEpochMs }
    }

    private data class IncidentPresentationBundle(
        val incident: com.example.trackme.domain.model.IncidentRecord,
        val timeline: List<com.example.trackme.domain.model.IncidentTimelineEntry>,
        val notes: List<IncidentCaseNote>,
        val attachments: List<IncidentAttachmentReference>,
        val evidenceExports: List<IncidentEvidenceExport>,
        val commands: List<DeviceCommand>,
        val lastKnownLocation: LocationSnapshot?,
        val evidenceChain: List<IncidentCaseEntry>,
    )

    private data class IncidentBaseBundle(
        val incident: com.example.trackme.domain.model.IncidentRecord,
        val timeline: List<com.example.trackme.domain.model.IncidentTimelineEntry>,
        val notes: List<IncidentCaseNote>,
        val attachments: List<IncidentAttachmentReference>,
        val evidenceExports: List<IncidentEvidenceExport>,
    )

    private companion object {
        const val DEFAULT_ACTOR_LABEL = "Local operator"
    }
}
