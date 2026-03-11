package com.example.trackme.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Append-only event record. We intentionally do not define update/delete DAO operations.
 */
@Entity(tableName = "audit_events")
data class AuditEventEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val type: String,
    val summary: String,
    val metadataJson: String,
    val createdAtEpochMs: Long,
    val previousHash: String?,
    val eventHash: String
)
