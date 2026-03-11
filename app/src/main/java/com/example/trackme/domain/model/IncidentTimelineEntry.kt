package com.example.trackme.domain.model

data class IncidentTimelineEntry(
    val id: Long,
    val incidentId: String,
    val state: IncidentState,
    val action: String,
    val summary: String,
    val metadataJson: String,
    val createdAtEpochMs: Long
)
