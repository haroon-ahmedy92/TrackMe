package com.example.trackme.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "incident_evidence_exports")
data class IncidentEvidenceExportEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val incidentId: String,
    val format: String,
    val reason: String,
    val requestedByLabel: String,
    val redactionSummary: String,
    val createdAtEpochMs: Long
)
