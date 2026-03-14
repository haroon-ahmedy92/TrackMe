package com.example.trackme.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "incident_attachment_references")
data class IncidentAttachmentReferenceEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val incidentId: String,
    val fileName: String,
    val description: String?,
    val mediaType: String,
    val byteSize: Long,
    val addedByLabel: String,
    val createdAtEpochMs: Long
)
