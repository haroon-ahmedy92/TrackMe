package com.example.trackme.domain.usecase

import com.example.trackme.core.TimeProvider
import com.example.trackme.domain.incident.IncidentAuditEvents
import com.example.trackme.domain.incident.IncidentStateMachine
import com.example.trackme.domain.incident.IncidentTrigger
import com.example.trackme.domain.model.IncidentRecord
import com.example.trackme.domain.model.IncidentTimelineEntry
import com.example.trackme.domain.repository.AuditRepository
import com.example.trackme.domain.repository.IncidentActionScheduler
import com.example.trackme.domain.repository.IncidentNotificationGateway
import com.example.trackme.domain.repository.IncidentRepository
import java.util.UUID
import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

class ManageIncidentLifecycleUseCase @Inject constructor(
    private val incidentRepository: IncidentRepository,
    private val incidentStateMachine: IncidentStateMachine,
    private val requestRemoteActionUseCase: RequestRemoteActionUseCase,
    private val setLostModeUseCase: SetLostModeUseCase,
    private val incidentActionScheduler: IncidentActionScheduler,
    private val incidentNotificationGateway: IncidentNotificationGateway,
    private val auditRepository: AuditRepository,
    private val timeProvider: TimeProvider,
    private val json: Json
) {
    fun observeCurrentIncident(): Flow<IncidentRecord> = incidentRepository.observeCurrentIncident()

    fun observeTimeline(limit: Int = DEFAULT_TIMELINE_LIMIT): Flow<List<IncidentTimelineEntry>> {
        return incidentRepository.observeTimeline(limit = limit)
    }

    suspend fun markAsLost(
        ticketReference: String,
        recoveryMessage: String,
        lostModeHours: Int = DEFAULT_LOST_WINDOW_HOURS
    ): Result<Unit> = runCatching {
        val ticket = ticketReference.trim()
        require(ticket.isNotBlank()) { "Ticket reference is required." }
        val message = recoveryMessage.trim().ifBlank { DEFAULT_RECOVERY_MESSAGE }

        val now = timeProvider.nowEpochMillis()
        val current = incidentRepository.getCurrentIncident()
        val nextState = incidentStateMachine.transition(current.state, IncidentTrigger.MarkSuspectedLost)
        val incidentId = current.incidentId ?: UUID.randomUUID().toString()
        val lostUntil = now + lostModeHours.coerceAtLeast(1) * ONE_HOUR_MS

        val updated = current.copy(
            incidentId = incidentId,
            state = nextState,
            ticketReference = ticket,
            recoveryMessage = message,
            createdAtEpochMs = current.createdAtEpochMs ?: now,
            updatedAtEpochMs = now,
            lostModeUntilEpochMs = lostUntil,
            wipeScheduledAtEpochMs = null,
            pendingWipeReason = null
        )

        incidentRepository.upsertCurrentIncident(updated)
        appendTimeline(
            incident = updated,
            action = "MARK_SUSPECTED_LOST",
            summary = "Device marked as suspected lost",
            metadata = mapOf("ticketReference" to ticket, "lostModeUntilEpochMs" to lostUntil.toString())
        )
        setLostModeUseCase.enable(lostUntil)
        val notifyResult = incidentNotificationGateway.notifyEscalation(
            title = "Recovery Incident Started",
            body = message
        )
        auditRepository.appendEvent(
            type = IncidentAuditEvents.INCIDENT_MARKED_LOST,
            summary = "Incident transitioned to suspected lost",
            metadata = mapOf(
                "incidentId" to incidentId,
                "ticketReference" to ticket,
                "lostModeUntilEpochMs" to lostUntil.toString(),
                "notificationEscalation" to (if (notifyResult.isSuccess) "success" else "failure")
            )
        )
    }

    suspend fun confirmStolen(
        elevatedConfirmationText: String,
        reason: String
    ): Result<Unit> = runCatching {
        require(elevatedConfirmationText.trim() == ELEVATED_CONFIRMATION_PHRASE) {
            "Elevated confirmation phrase mismatch."
        }
        val current = requireIncident(incidentRepository.getCurrentIncident())
        val nextState = incidentStateMachine.transition(
            current.state,
            IncidentTrigger.ConfirmStolen(elevatedConfirmed = true)
        )
        val now = timeProvider.nowEpochMillis()
        val extendedLostUntil = maxOf(
            current.lostModeUntilEpochMs ?: 0L,
            now + CONFIRMED_STOLEN_WINDOW_HOURS * ONE_HOUR_MS
        )
        val updated = current.copy(
            state = nextState,
            updatedAtEpochMs = now,
            lostModeUntilEpochMs = extendedLostUntil
        )
        incidentRepository.upsertCurrentIncident(updated)
        appendTimeline(
            incident = updated,
            action = "CONFIRM_STOLEN",
            summary = "Incident confirmed stolen with elevated confirmation",
            metadata = mapOf("reason" to reason.trim())
        )
        setLostModeUseCase.enable(extendedLostUntil)
        val notifyResult = incidentNotificationGateway.notifyEscalation(
            title = "Confirmed Stolen Device",
            body = "Ticket ${updated.ticketReference} requires immediate incident response."
        )
        auditRepository.appendEvent(
            type = IncidentAuditEvents.INCIDENT_CONFIRMED_STOLEN,
            summary = "Incident transitioned to confirmed stolen",
            metadata = mapOf(
                "incidentId" to updated.requireIncidentId(),
                "reason" to reason.trim(),
                "lostModeUntilEpochMs" to extendedLostUntil.toString(),
                "notificationEscalation" to (if (notifyResult.isSuccess) "success" else "failure")
            )
        )
    }

    suspend fun requestRemoteLock(reason: String): Result<Unit> = runCatching {
        val current = requireIncident(incidentRepository.getCurrentIncident())
        val sanitizedReason = reason.trim()
        require(sanitizedReason.isNotBlank()) { "Remote lock reason is required." }
        require(incidentStateMachine.canRequestRemoteLock(current.state)) {
            "Remote lock is only allowed in suspected-lost or confirmed-stolen states."
        }
        val lockResult = requestRemoteActionUseCase.requestLock(current.ticketReference)
        appendTimeline(
            incident = current,
            action = "REMOTE_LOCK_DECISION",
            summary = "Remote lock decision executed",
            metadata = mapOf(
                "reason" to sanitizedReason,
                "result" to (if (lockResult.isSuccess) "success" else "failure")
            )
        )
        auditRepository.appendEvent(
            type = IncidentAuditEvents.INCIDENT_REMOTE_LOCK_DECISION,
            summary = "Remote lock decision evaluated",
            metadata = mapOf(
                "incidentId" to current.requireIncidentId(),
                "state" to current.state.name,
                "reason" to sanitizedReason,
                "result" to (if (lockResult.isSuccess) "success" else "failure")
            )
        )
        lockResult.getOrThrow()
    }

    suspend fun requestOrScheduleRemoteWipe(
        reason: String,
        delayMinutes: Int,
        elevatedConfirmationText: String,
        acknowledgedTradeoff: Boolean,
        confirmedWipeIntent: Boolean
    ): Result<Unit> = runCatching {
        val current = requireIncident(incidentRepository.getCurrentIncident())
        require(incidentStateMachine.canRequestRemoteWipe(current.state)) {
            "Remote wipe is only allowed after incident is confirmed stolen."
        }
        require(elevatedConfirmationText.trim() == ELEVATED_CONFIRMATION_PHRASE) {
            "Elevated confirmation phrase mismatch."
        }
        require(acknowledgedTradeoff) {
            "You must acknowledge the wipe tradeoff text."
        }
        require(confirmedWipeIntent) {
            "You must explicitly confirm wipe intent."
        }
        val wipeReason = reason.trim()
        require(wipeReason.isNotBlank()) {
            "Remote wipe reason is required."
        }

        if (delayMinutes > 0) {
            require(delayMinutes >= MIN_DELAYED_WIPE_MINUTES) {
                "Delayed wipe must be at least $MIN_DELAYED_WIPE_MINUTES minutes."
            }
            val now = timeProvider.nowEpochMillis()
            val executeAt = now + delayMinutes * ONE_MINUTE_MS
            val updated = current.copy(
                wipeScheduledAtEpochMs = executeAt,
                pendingWipeReason = wipeReason,
                updatedAtEpochMs = now
            )
            incidentRepository.upsertCurrentIncident(updated)
            incidentActionScheduler.scheduleDelayedWipe(executeAtEpochMs = executeAt)
            appendTimeline(
                incident = updated,
                action = "REMOTE_WIPE_DELAYED",
                summary = "Remote wipe scheduled with delay",
                metadata = mapOf(
                    "delayMinutes" to delayMinutes.toString(),
                    "executeAtEpochMs" to executeAt.toString(),
                    "reason" to wipeReason
                )
            )
            auditRepository.appendEvent(
                type = IncidentAuditEvents.INCIDENT_REMOTE_WIPE_DELAYED,
                summary = "Remote wipe delayed by operator decision",
                metadata = mapOf(
                    "incidentId" to updated.requireIncidentId(),
                    "delayMinutes" to delayMinutes.toString(),
                    "executeAtEpochMs" to executeAt.toString(),
                    "reason" to wipeReason,
                    "tradeoffText" to WIPE_TRADEOFF_TEXT
                )
            )
            return@runCatching
        }

        executeWipe(current = current, reason = wipeReason, source = "immediate")
    }

    suspend fun executeDelayedWipeIfDue(source: String): Result<Unit> = runCatching {
        val current = incidentRepository.getCurrentIncident()
        if (current.incidentId == null) return@runCatching
        val executeAt = current.wipeScheduledAtEpochMs ?: return@runCatching
        if (timeProvider.nowEpochMillis() < executeAt) return@runCatching

        executeWipe(
            current = current,
            reason = current.pendingWipeReason ?: "Delayed wipe window reached",
            source = source
        )
    }

    suspend fun recover(reason: String): Result<Unit> = runCatching {
        val current = requireIncident(incidentRepository.getCurrentIncident())
        val sanitizedReason = reason.trim()
        require(sanitizedReason.isNotBlank()) { "Recovery reason is required." }
        val nextState = incidentStateMachine.transition(current.state, IncidentTrigger.MarkRecovered)
        val now = timeProvider.nowEpochMillis()
        val updated = current.copy(
            state = nextState,
            updatedAtEpochMs = now,
            wipeScheduledAtEpochMs = null,
            pendingWipeReason = null
        )
        incidentRepository.upsertCurrentIncident(updated)
        incidentActionScheduler.cancelDelayedWipe()
        setLostModeUseCase.disable()
        appendTimeline(
            incident = updated,
            action = "RECOVER_DEVICE",
            summary = "Incident marked recovered",
            metadata = mapOf("reason" to sanitizedReason)
        )
        auditRepository.appendEvent(
            type = IncidentAuditEvents.INCIDENT_RECOVERED,
            summary = "Incident transitioned to recovered",
            metadata = mapOf("incidentId" to updated.requireIncidentId(), "reason" to sanitizedReason)
        )
    }

    suspend fun cancel(reason: String): Result<Unit> = runCatching {
        val current = incidentRepository.getCurrentIncident()
        val sanitizedReason = reason.trim()
        require(sanitizedReason.isNotBlank()) { "Cancellation reason is required." }
        val nextState = incidentStateMachine.transition(current.state, IncidentTrigger.CancelIncident)
        val now = timeProvider.nowEpochMillis()
        val updated = current.copy(
            state = nextState,
            updatedAtEpochMs = now,
            lostModeUntilEpochMs = null,
            wipeScheduledAtEpochMs = null,
            pendingWipeReason = null
        )
        incidentRepository.upsertCurrentIncident(updated)
        incidentActionScheduler.cancelDelayedWipe()
        setLostModeUseCase.disable()
        if (updated.incidentId != null) {
            appendTimeline(
                incident = updated,
                action = "CANCEL_INCIDENT",
                summary = "Incident cancelled",
                metadata = mapOf("reason" to sanitizedReason)
            )
            auditRepository.appendEvent(
                type = IncidentAuditEvents.INCIDENT_CANCELLED,
                summary = "Incident cancelled by operator",
                metadata = mapOf("incidentId" to updated.requireIncidentId(), "reason" to sanitizedReason)
            )
        }
    }

    suspend fun decommission(reason: String): Result<Unit> = runCatching {
        val current = requireIncident(incidentRepository.getCurrentIncident())
        val sanitizedReason = reason.trim()
        require(sanitizedReason.isNotBlank()) { "Decommission reason is required." }
        val nextState = incidentStateMachine.transition(current.state, IncidentTrigger.Decommission)
        val now = timeProvider.nowEpochMillis()
        val updated = current.copy(
            state = nextState,
            updatedAtEpochMs = now,
            lostModeUntilEpochMs = null,
            wipeScheduledAtEpochMs = null,
            pendingWipeReason = null
        )
        incidentRepository.upsertCurrentIncident(updated)
        incidentActionScheduler.cancelDelayedWipe()
        setLostModeUseCase.disable()
        appendTimeline(
            incident = updated,
            action = "DECOMMISSION_DEVICE",
            summary = "Incident marked decommissioned",
            metadata = mapOf("reason" to sanitizedReason)
        )
        auditRepository.appendEvent(
            type = IncidentAuditEvents.INCIDENT_DECOMMISSIONED,
            summary = "Device decommissioned after incident workflow",
            metadata = mapOf("incidentId" to updated.requireIncidentId(), "reason" to sanitizedReason)
        )
    }

    private suspend fun executeWipe(current: IncidentRecord, reason: String, source: String) {
        val wipeResult = requestRemoteActionUseCase.requestWipe(current.ticketReference)
        if (wipeResult.isFailure) {
            appendTimeline(
                incident = current,
                action = "REMOTE_WIPE_FAILED",
                summary = "Remote wipe attempt failed",
                metadata = mapOf(
                    "reason" to reason,
                    "source" to source,
                    "result" to "failure"
                )
            )
            auditRepository.appendEvent(
                type = IncidentAuditEvents.INCIDENT_REMOTE_WIPE_FAILED,
                summary = "Remote wipe execution failed",
                metadata = mapOf(
                    "incidentId" to current.requireIncidentId(),
                    "source" to source,
                    "reason" to reason
                )
            )
            wipeResult.getOrThrow()
        }

        val now = timeProvider.nowEpochMillis()
        val nextState = incidentStateMachine.transition(current.state, IncidentTrigger.MarkWiped)
        val updated = current.copy(
            state = nextState,
            updatedAtEpochMs = now,
            wipeScheduledAtEpochMs = null,
            pendingWipeReason = null
        )
        incidentRepository.upsertCurrentIncident(updated)
        incidentActionScheduler.cancelDelayedWipe()
        setLostModeUseCase.disable()
        appendTimeline(
            incident = updated,
            action = "REMOTE_WIPE_EXECUTED",
            summary = "Remote wipe executed",
            metadata = mapOf(
                "source" to source,
                "reason" to reason
            )
        )
        auditRepository.appendEvent(
            type = IncidentAuditEvents.INCIDENT_REMOTE_WIPE_EXECUTED,
            summary = "Remote wipe executed and incident moved to wiped state",
            metadata = mapOf(
                "incidentId" to updated.requireIncidentId(),
                "source" to source,
                "reason" to reason
            )
        )
    }

    private suspend fun appendTimeline(
        incident: IncidentRecord,
        action: String,
        summary: String,
        metadata: Map<String, String>
    ) {
        val incidentId = incident.requireIncidentId()
        incidentRepository.appendTimelineEntry(
            IncidentTimelineEntry(
                id = 0,
                incidentId = incidentId,
                state = incident.state,
                action = action,
                summary = summary,
                metadataJson = json.encodeToString(metadata.toSortedMap()),
                createdAtEpochMs = timeProvider.nowEpochMillis()
            )
        )
    }

    private fun requireIncident(current: IncidentRecord): IncidentRecord {
        require(current.incidentId != null) { "No active incident record." }
        return current
    }

    private fun IncidentRecord.requireIncidentId(): String {
        return incidentId ?: throw IllegalStateException("Missing incident id.")
    }

    companion object {
        const val ELEVATED_CONFIRMATION_PHRASE = "CONFIRM_STOLEN"
        const val WIPE_TRADEOFF_TEXT =
            "Wiping may protect organization data but may reduce chances of physical recovery."

        private const val DEFAULT_LOST_WINDOW_HOURS = 12
        private const val CONFIRMED_STOLEN_WINDOW_HOURS = 24
        private const val DEFAULT_TIMELINE_LIMIT = 200
        private const val MIN_DELAYED_WIPE_MINUTES = 15
        private const val DEFAULT_RECOVERY_MESSAGE = "This protected device is marked as lost. Please contact support."
        private const val ONE_HOUR_MS = 60 * 60 * 1000L
        private const val ONE_MINUTE_MS = 60 * 1000L
    }
}
