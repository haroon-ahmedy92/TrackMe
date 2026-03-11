package com.example.trackme.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "incident_state")
data class IncidentStateEntity(
    @PrimaryKey val id: Int = SINGLETON_ID,
    val incidentId: String?,
    val state: String,
    val ticketReference: String,
    val recoveryMessage: String?,
    val createdAtEpochMs: Long?,
    val updatedAtEpochMs: Long?,
    val lostModeUntilEpochMs: Long?,
    val wipeScheduledAtEpochMs: Long?,
    val pendingWipeReason: String?
) {
    companion object {
        const val SINGLETON_ID = 1
    }
}
