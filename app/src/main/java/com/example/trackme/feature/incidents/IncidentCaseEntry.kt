package com.example.trackme.feature.incidents

enum class IncidentCaseEntryKind {
    STATUS_CHANGE,
    LOCATION,
    COMMAND,
    NOTE,
    AUDIT
}

data class IncidentCaseEntry(
    val id: String,
    val kind: IncidentCaseEntryKind,
    val title: String,
    val summary: String,
    val occurredAtEpochMs: Long,
    val actorLabel: String? = null,
    val mutable: Boolean = false,
)
