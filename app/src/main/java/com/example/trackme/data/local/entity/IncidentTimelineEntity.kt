package com.example.trackme.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "incident_timeline")
data class IncidentTimelineEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val incidentId: String,
    val state: String,
    val action: String,
    val summary: String,
    val metadataJson: String,
    val createdAtEpochMs: Long
)
