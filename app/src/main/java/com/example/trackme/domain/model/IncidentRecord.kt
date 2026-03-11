package com.example.trackme.domain.model

data class IncidentRecord(
    val incidentId: String? = null,
    val state: IncidentState = IncidentState.NORMAL,
    val ticketReference: String = "",
    val recoveryMessage: String? = null,
    val createdAtEpochMs: Long? = null,
    val updatedAtEpochMs: Long? = null,
    val lostModeUntilEpochMs: Long? = null,
    val wipeScheduledAtEpochMs: Long? = null,
    val pendingWipeReason: String? = null
)
