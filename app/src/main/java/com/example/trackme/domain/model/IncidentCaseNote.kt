package com.example.trackme.domain.model

data class IncidentCaseNote(
    val id: Long,
    val incidentId: String,
    val authorLabel: String,
    val body: String,
    val isPinned: Boolean,
    val createdAtEpochMs: Long,
    val updatedAtEpochMs: Long
)
