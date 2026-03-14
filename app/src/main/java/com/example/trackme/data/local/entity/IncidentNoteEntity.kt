package com.example.trackme.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "incident_notes")
data class IncidentNoteEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val incidentId: String,
    val authorLabel: String,
    val body: String,
    val isPinned: Boolean,
    val createdAtEpochMs: Long,
    val updatedAtEpochMs: Long
)
