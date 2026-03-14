package com.example.trackme.domain.model

enum class IncidentEvidenceExportFormat {
    JSON,
    PDF
}

data class IncidentEvidenceExport(
    val id: Long,
    val incidentId: String,
    val format: IncidentEvidenceExportFormat,
    val reason: String,
    val requestedByLabel: String,
    val redactionSummary: String,
    val createdAtEpochMs: Long
)
