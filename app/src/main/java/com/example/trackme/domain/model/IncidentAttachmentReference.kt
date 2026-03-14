package com.example.trackme.domain.model

data class IncidentAttachmentReference(
    val id: Long,
    val incidentId: String,
    val fileName: String,
    val description: String?,
    val mediaType: String,
    val byteSize: Long,
    val addedByLabel: String,
    val createdAtEpochMs: Long
)
